import shutil
import os.path
from json import dumps
from pathlib import Path

from .formats import logger
from .compiler import compile_operations


class Ponder:
    """ 创建一个思索类, 用于记录用户每一步的操作, 并在编译器中重放并编译为Minecraft命令. """

    def __init__(self, size: int):
        """
        初始化思索类, 并生成棋盘格地板.
        :param size: 边长
        """

        if size > 8 and size % 3 != 0:
            logger.critical('初始化思索失败: 边长超过7的大型棋盘格尺寸应为3的倍数')

        self.size = size
        self.commands = []  # 记录用户的命令

    def block(self, time: int, pos: tuple, block: str, state: dict = {}, nbt: dict = {}):
        """
        对一个方块进行放置, 也可以替换同一个方块或改变其状态.
        :param time: 放置时间, 单位为rt(红石刻, 1/10秒)
        :param pos: (x, y, z) 坐标 地板位置x, y, z轴最小处为(0, 0, 0)
        :param block: 方块名称, 'minecraft:'可省略
        :param state: 方块状态, 如 {'facing': 'north'}
        :param nbt: 方块NBT数据, 如 {'CustomName': 'My Entity'}
        """

        self.commands.append({
            'type': 'place',
            'time': time,
            'pos': pos,
            'block': block,
            'state': state,
            'nbt': nbt
        })

    def remove(self, time: int, pos: tuple, animation: str = 'y+'):
        """
        对一个方块进行移除.
        :param time: 移除时间, 单位为rt(红石刻, 1/10秒)
        :param pos: (x, y, z) 坐标 地板位置x, y, z轴最小处为(0, 0, 0)
        :param animation: 移除动画, 可选: 'y+', 'x+', 'x-', 'z+', 'z-', 'destroy'
        """

        self.commands.append({
            'type': 'remove',
            'time': time,
            'pos': pos,
            'animation': animation
        })

    def text(self, time: int, pos: tuple, text: str, duration: int = 20, rotation: list = [0, 0, 0]):
        """
        显示一段文字.
        :param time: 显示时间, 单位为rt(红石刻, 1/10秒)
        :param pos: (x, y, z) 坐标 地板位置x, y, z轴最小处为(0, 0, 0)
        :param text: 文字内容
        :param rotation: (yaw, pitch, roll) 旋转角度, 单位为度(°)
        :param duration: 持续时间, 单位为rt(红石刻, 1/10秒)
        """

        self.commands.append({
            'type': 'text',
            'time': time,
            'pos': pos,
            'text': text,
            'rotation': rotation,
            'duration': duration
        })

    def entity(self, time: int, pos: tuple, name: str, nbt: dict = {}):
        """
        生成一个实体.
        :param time: 显示时间, 单位为rt(红石刻, 1/10秒)
        :param pos: (x, y, z) 坐标 地板位置x, y, z轴最小处为(0, 0, 0)
        :param name: 实体名称, 如 'minecraft:cow'
        :param nbt: 实体NBT数据, 如 {'CustomName': 'My Cow'}
        """

        self.commands.append({
            'type': 'entity',
            'time': time,
            'pos': pos,
            'name': name,
            'nbt': nbt
        })

    def command(self, time: int, command: str):
        """
        执行一个自定义命令.
        注意: 在需要使用坐标的场景中, 需要使用<你的坐标>进行转义以支持坐标偏移, 如 tp 1 1 1 -> tp <1 1 1>
        :param time: 执行时间, 单位为rt(红石刻, 1/10秒)
        :param command: 要执行的命令, 如 'gamerule doDaylightCycle false' 不允许前导/
        """

        self.commands.append({
            'type': 'command',
            'time': time,
            'command': command
        })

    def compile(
        self,
        version: bool = True,
        pos_offset: tuple = (0, 0, 0),
        ponder_name: str = "ponders",
        output_dir: str = "."
    ):
        """
        编译思索对象为Minecraft数据包
        :param ponder: 你的思索对象
        :param version: 是否为1.21+版本
        :param ponder_name: 你的思索名称
        :param pos_offset: 偏移坐标
        :param output_dir: 输出目录
        :return: 输出路径
        """
        logger.info(f"正在编译思索为数据包...")
        logger.debug(f"传入参数: version={version}, pos_offset={pos_offset}, ponder_name={ponder_name}, "
                    f"output_dir={output_dir}")

        datapack_dir = Path(output_dir) / ponder_name

        # 检测输出的zip文件是否存在
        if os.path.exists(f'{output_dir}/{ponder_name}.zip'):
            logger.warning(f"输出文件 {ponder_name}.zip 已存在, 可能覆盖已有文件, 是否继续? (y/n)")
            if input().lower() != "y":
                logger.info(f"已取消编译.")
                return

        commands = compile_operations(self, pos_offset)

        # 生成数据包主结构
        if not datapack_dir.exists():
            datapack_dir.mkdir(parents=True)

        # 生成pack.mcmeta
        meta_data = {
            "pack": {
                "pack_format": 16,
                "supported_formats": [16, 39],
                "description": "使用 creepe_ponder 生成的思索数据包"
            }
        }
        meta_file = datapack_dir / "pack.mcmeta"
        meta_file.write_text(dumps(meta_data), encoding="Utf-8")

        # 生成用于存放函数的文件夹
        function_dir = (datapack_dir / f"data/{ponder_name}") / ("function" if version else "functions")
        function_dir.mkdir(parents=True)

        functions = {}  # 存放函数的列表
        # 整理每个时刻工作的指令
        for command in commands:
            time, command_str = command
            if time in functions:
                functions[time].append(command_str)
                continue
            functions[time] = ['# Generated by creepe_ponder', command_str]

        # 将指令写入函数文件
        for time, command_list in functions.items():
            function_file = function_dir / f"_{time}.mcfunction"
            function_file.write_text('\n'.join(command_list))

        # 生成主函数文件
        command_list = ['# Generated by creepe_ponder']

        # 使用/schedule指令让函数文件按顺序执行
        for time in functions.keys():
            command_list.append(f"schedule function {ponder_name}:{time} {time * 2 + 1} append")  # rt转为gt, 并增加一个偏移量

        main_function_file = function_dir / "main.mcfunction"
        main_function_file.write_text('\n'.join(command_list))

        # 打包数据包
        shutil.make_archive(datapack_dir, "zip", datapack_dir)

        # 删除临时文件
        shutil.rmtree(datapack_dir)

        logger.info(f"编译完成, 共在{len(functions)}个时刻输出{len(commands)}条指令, "
                    f"总动画长度: {max(functions.keys()) / 20}秒, 输出路径: {output_dir}/{ponder_name}.zip")


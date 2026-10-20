#!/usr/bin/env python3
"""中文导读：启动真实 LEAN 的离线历史回测，不在这里重写回测引擎。

使用方式：python3 scripts/run_lean.py first；其他课程入口见 configs/curriculum.json。
--prepare-only 只生成配置，适合先学习启动参数，不实际启动 Docker。
官方源代码保留完整实时交易架构；本启动器只开放回测入口。
"""

# argparse 负责解析命令行参数，例如选择 first、data 或 factors。
import argparse
# datetime 用于给每次运行生成独立的结果目录名。
import datetime
# json 用于读写引擎配置、版本清单和回测结果。
import json
# platform 用于识别电脑 CPU 架构，从而选用对应的官方镜像。
import platform
# shutil.which 用于在系统 PATH 中查找 docker 可执行程序。
import shutil
# subprocess 用于执行 Git、Docker 等外部程序，不负责计算交易收益。
import subprocess
# Path 用对象方式组合路径，减少手工拼接路径分隔符造成的错误。
from pathlib import Path

# __file__ 是当前脚本位置；resolve 得到绝对路径；parents[1] 指向仓库根目录。
# 因此代码定位文件不依赖你碰巧在哪个目录中启动它。
ROOT = Path(__file__).resolve().parents[1]


# 官方配置允许 // 行注释，标准 json.loads 却不允许；先去掉字符串外部的行注释。
# 不能简单按 // 截断每行，因为 "https://example.com" 中的 // 是字符串的一部分。
def read_json_comments(text):
    # out 累积需要保留的字符，最终重新拼成 JSON 文本。
    out = []
    # inside 表示当前是否位于双引号包围的 JSON 字符串内部。
    inside = False
    # escape 表示前一个字符是反斜杠，当前字符应按转义字符处理。
    escape = False
    # i 是扫描位置，从文本第一个字符开始。
    i = 0
    # 逐个扫描字符，直到抵达文本末尾。
    while i < len(text):
        # 取出当前字符；这里的索引从 0 开始。
        ch = text[i]
        # 字符串中的字符都必须保留，包括可能出现的斜杠。
        if inside:
            # 将该字符加入输出缓冲。
            out.append(ch)
            # 如果前一字符是反斜杠，就只消费这一次转义状态。
            if escape:
                # 转义处理结束；当前双引号即使存在，也不能结束字符串。
                escape = False
            # 当前反斜杠让下一个字符进入转义状态。
            elif ch == '\\':
                # 下一轮先处理 escape 分支。
                escape = True
            # 非转义的双引号表示 JSON 字符串结束。
            elif ch == '"':
                # 后续字符重新按字符串外部的语法解释。
                inside = False
            # 当前字符处理完成，向右移动一位。
            i += 1
            # 跳过本轮剩余逻辑，避免把字符串中的 // 当成注释。
            continue
        # 在字符串外遇到双引号，说明一个新的字符串开始。
        if ch == '"':
            # 进入字符串状态。
            inside = True
            # 双引号本身也属于合法 JSON，不能丢掉。
            out.append(ch)
            # 扫描位置前移。
            i += 1
            # 下一轮由字符串内部逻辑接手。
            continue
        # 只在字符串外识别 // 行注释。
        if text[i:i+2] == '//':
            # 跳过注释直到换行或文本结束，不把注释内容交给 JSON 解析器。
            while i < len(text) and text[i] != '\n':
                # 前进一位；循环条件保护末尾索引不越界。
                i += 1
            # 下一轮会正常处理换行；本轮不输出注释。
            continue
        # 普通字符，例如大括号、逗号、数字和空白，原样保留。
        out.append(ch)
        # 继续扫描下一个字符。
        i += 1
    # 将字符列表合为字符串，再解析成 Python 字典；错误的 JSON 会直接报错。
    # 这个小解析器只处理官方文件使用的 // 注释，不是通用 JSON5 解析器。
    return json.loads(''.join(out))


# 为指定课程生成配置；output 是本次结果目录，函数返回生成的配置文件路径。
def prepare(lesson, output, parameters=None):
    # 课程清单只选择算法和验收条件，不允许它打开实时交易。
    course = json.loads((ROOT / 'configs/curriculum.json').read_text())[lesson]
    # upstream 指向完整官方源码的 Git 子模块，而不是旧的 legacy 引擎。
    upstream = ROOT / 'vendor/lean'
    # 以官方配置为基础，保留必要的系统处理器和数据读取规则。
    config = read_json_comments((upstream / 'Launcher/config.json').read_text())
    # 取出官方定义的回测环境，包括历史数据、交易事务及结果处理器。
    env = config['environments']['backtesting']
    # 本次生成的运行配置只包含回测环境；官方源码中的其他环境没有被删除。
    config['environments'] = {'backtesting': env}
    # 覆盖与这次本地课程有关的字段，其余配置沿用官方默认值。
    config.update({
        # 使用历史回测处理器组合，不使用实时券商处理器。
        'environment': 'backtesting',
        # 当前作业不是实时模式；未来纸盘/实盘的配置会单独实现。
        'live-mode': False,
        # 算法结束后让引擎退出，便于脚本判断是否完成。
        'close-automatically': True,
        # 以下路径都是容器内部路径，稍后由 Docker 绑定到本机目录。
        'data-folder': '/Lean/Data',
        # LEAN 将结果 JSON、订单事件及日志写入这个目录。
        'results-destination-folder': '/Results',
        # Object Store 是 LEAN 的对象存储位置，当前也放进本次结果目录。
        'object-store-root': '/Results/storage',
        # 策略采用 Python 编写，实际执行这些策略的 LEAN 核心仍是 C#。
        'algorithm-language': 'Python',
        # 选择要实例化的类名；必须和对应 Python 文件中的类声明一致。
        'algorithm-type-name': course['class'],
        # 课程清单给出所选 Python 文件的容器内绝对路径。
        'algorithm-location': course['path'],
        # 帮助容器内的 Python 查找官方示例依赖和引擎提供的模块。
        'python-additional-paths': ['/Upstream/Algorithm.Python', '/Lean/Launcher/bin/Debug'],
        # 本地示例不需要 QuantConnect 云账户，这里的 0 是作业标识占位值。
        'job-user-id': '0',
        # 不传入云平台 API 密钥；也不会在此读取本机 .env。
        'api-access-token': '',
        # 当前没有绑定云组织。
        'job-organization-id': '',
        # 给本次算法一个可辨认的标识，方便在输出文件名和日志中定位。
        'algorithm-id': 'USQuant-LEAN-' + lesson,
        # 本地课程项目标识，不是券商账户编号。
        'job-project-id': '0'
    })
    # 参数只传给算法；不会修改数据处理器、账户或运行模式。
    config['parameters'] = parameters or {}
    # 开发检查：选用的官方回测环境也必须明确关闭实时模式。
    # assert 是检查，不是唯一防线；下面的断网运行和无凭据挂载同样重要。
    assert config['environments']['backtesting']['live-mode'] is False
    # 如果目录不存在就创建；parents=True 也会创建缺少的父目录。
    output.mkdir(parents=True, exist_ok=True)
    # 每次运行保存实际配置，而不是只记住一个不断变化的全局文件。
    path = output / 'config.json'
    # 标准 JSON 不允许注释，所以把教学说明留在本脚本及中文字段说明里。
    path.write_text(json.dumps(config, indent=2))
    # 返回路径，让调用方或教学检查知道配置写在哪里。
    return path


# 主函数负责准备、启动及验证输出；不会自行挑选因子或计算回测成交。
def main():
    # 以模块说明作为命令行帮助，用户可用 --help 查看。
    parser = argparse.ArgumentParser(description=__doc__)
    # 读取可用课程，并保留 official 与 first 这两个原入口。
    courses = json.loads((ROOT / 'configs/curriculum.json').read_text())
    # 唯一必填参数是课程名；不接受 live 参数，避免把本课入口当成实盘入口。
    parser.add_argument('lesson', choices=list(courses))
    # 此开关只准备文件，不启动 Docker；默认值为 False。
    parser.add_argument('--prepare-only', action='store_true')
    # 可重复传入算法实验参数，例如 --parameter cost-bps=20。
    parser.add_argument('--parameter', action='append', default=[])
    # 将命令行输入解析成 args.lesson、args.prepare_only 等属性。
    args = parser.parse_args()
    # 为该课程检查参数名，拒绝把任意配置项伪装成算法参数。
    parameters = {}
    # 逐条解析用户给出的 name=value。
    for item in args.parameter:
        # partition 保留等号之后的文本，避免对多个等号错误拆分。
        key, separator, value = item.partition('=')
        # 只接受课程清单明确声明的算法参数。
        if not separator or key not in courses[args.lesson].get('parameters', []):
            # 参数错误时停止，不启动容器。
            parser.error('Unsupported course parameter: ' + item)
        # 保存已经验证的参数。
        parameters[key] = value
    # 用本机时间、微秒和课程名生成目录；它只用于文件命名，不是交易时间。
    output = ROOT / 'results' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + args.lesson)
    # 写入这次实际使用的 LEAN 配置。
    prepare(args.lesson, output, parameters)
    # 读取固定版本清单；不依赖会随时间变化的 latest 镜像标签。
    lock = json.loads((ROOT / 'configs/engine-lock.json').read_text())
    # Apple 芯片通常返回 arm64，部分 Linux 返回 aarch64；其余按 AMD64 路线选择。
    arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'amd64'
    # 选取与本机架构相配的官方镜像及其内容摘要。
    image = lock['images'][arch]
    # 记录来源信息，方便将来解释“这一次究竟运行了什么版本”。
    manifest = {
        # 向 Git 查询实际源码提交号；源码版本与预编译镜像版本是独立记录的。
        'source_commit': subprocess.check_output(['git', '-C', str(ROOT / 'vendor/lean'), 'rev-parse', 'HEAD'], text=True).strip(),
        # 这里记录真正运行的二进制镜像；修改 C# 源码不会自动改变它。
        'runtime_image': image,
        # 记录运行架构，便于跨电脑比较环境。
        'architecture': arch,
        # 记录课程入口。
        'lesson': args.lesson,
        # 明确这是一份离线历史回测，而不是券商纸盘成交记录。
        'mode': 'offline-backtesting'
    }
    # 将版本清单和回测配置放在一起；这份文件不包含交易密钥。
    (output / 'provenance.json').write_text(json.dumps(manifest, indent=2))
    # 用户只想查看配置时，在这里结束，不会隐式启动后续任务。
    if args.prepare_only:
        # 打印目录，方便点击或在 Finder 中寻找。
        print(output)
        # 结束主函数。
        return
    # 优先查 PATH；Mac 找不到 docker 时，再使用 Docker Desktop 的官方安装路径。
    docker = shutil.which('docker') or '/Applications/Docker.app/Contents/Resources/bin/docker'
    # 所有课程保留这个隔离的数据目录；第二课使用其中的导出快照。
    (ROOT / 'local-data').mkdir(exist_ok=True)
    # 用参数列表启动程序，而不是拼成 shell 文本，避免空格或特殊字符被误解释。
    command = [
        # Docker 客户端程序路径。
        docker,
        # run 表示从镜像创建并运行一个新容器。
        'run',
        # 运行结束后删除临时容器；绑定到本机的结果文件不会因此删除。
        '--rm',
        # 明确容器系统和 CPU 架构。
        '--platform', 'linux/' + arch,
        # 禁止容器网络访问；读取历史文件不需要连接券商。
        '--network', 'none',
        # 给课程容器限定最多约两个 CPU 核的计算配额。
        '--cpus', '2',
        # 限制容器内存，单位 g 表示 GiB 级内存额度，不是磁盘容量。
        '--memory', '4g',
        # 只读挂载官方样例数据，不把已有私有行情库挂进去冒充 LEAN 原生数据。
        '--mount', f'type=bind,src={ROOT / "vendor/lean/Data"},dst=/Lean/Data,readonly',
        # 只读挂载官方源码，供 official 课程读取 Python 示例。
        '--mount', f'type=bind,src={ROOT / "vendor/lean"},dst=/Upstream,readonly',
        # 只读挂载课程算法；容器不能回写修改我们正在学习的代码。
        '--mount', f'type=bind,src={ROOT / "lessons"},dst=/Lessons,readonly',
        # MySQL 导出的课程数据单独只读挂载；该目录不包含 .env。
        '--mount', f'type=bind,src={ROOT / "local-data"},dst=/CourseData,readonly',
        # 结果目录需要可写，才能保存订单事件、统计和日志。
        '--mount', f'type=bind,src={output},dst=/Results',
        # 指定官方引擎镜像；镜像自身的入口是 dotnet + LEAN Launcher。
        image,
        # 把配置位置传给引擎，而不是给宿主机 Python。
        '--config', '/Results/config.json'
    ]
    # 不传 --env-file，不挂载 .env、Docker 控制套接字或券商凭据。
    # 首次 Docker 客户端拉取镜像可能需要宿主机联网；容器运行本身仍然断网。
    with (output / 'console.log').open('w') as log:
        # stdout=PIPE 用于读取引擎输出；把标准错误合并进同一日志，避免遗漏报错。
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # 持续读取输出，直到容器程序结束并关闭输出流。
        for line in process.stdout:
            # 同时显示到终端；flush=True 让用户及时看到进展。
            print(line, end='', flush=True)
            # 将同一行写入文件，运行后还能复查过程。
            log.write(line)
        # 等待外部程序退出；code 通常为 0 表示进程层面正常结束。
        code = process.wait()
    # 无论成败都打印结果路径，便于定位日志。
    print('Results:', output)
    # 非零退出码表示启动或运行失败，直接传给调用方，不伪装成成功。
    if code:
        # SystemExit 设置当前脚本的退出状态。
        raise SystemExit(code)
    # 某些 LEAN 算法错误后进程也可能返回 0，因此还必须检查实际结果文件。
    # 排除配置、版本清单和订单事件文件，后者的结构不是主回测结果。
    candidates = [p for p in output.glob('*.json') if p.name not in ('config.json', 'provenance.json') and not p.name.endswith('-order-events.json')]
    # 收集包含统计字段的主结果或汇总结果。
    results = []
    # 对候选文件逐一解析。
    for path in candidates:
        # 真正读取 LEAN 产出的 JSON，而不是靠日志里出现了某个词判断成功。
        data = json.loads(path.read_text())
        # 只保留顶层为字典且有 statistics 字段的结果。
        if isinstance(data, dict) and 'statistics' in data:
            # 加入待验证结果列表。
            results.append(data)
    # 数据课可以合法地不交易，按各课最小订单数判断而非一律要求成交。
    minimum = courses[args.lesson]['min_orders']
    # 缺少统计或订单数不达标时，判定课程未完成。
    if not results or not any(int(r.get('statistics', {}).get('Total Orders', 0)) >= minimum for r in results):
        # 缺少完成结果或预期订单时提示查看日志。
        raise SystemExit('No completed result with orders; inspect console.log')
    # 即使结果有统计字段，也不能忽视其中声明的算法运行错误。
    if any(r.get('runtimeError') for r in results):
        # 报错退出，防止把部分输出当成完整成功结果。
        raise SystemExit('LEAN runtime error')
    # 高级课程在结束时执行断言并打印验收标记，避免把半途输出当成完成。
    marker = courses[args.lesson].get('marker')
    # 只在指定了标记的课程检查日志。
    if marker and marker not in (output / 'console.log').read_text():
        # 断言失败或没有执行到结尾，都不能算课程通过。
        raise SystemExit('Missing course acceptance marker: ' + marker)
    # 只有检查通过才显示成功；订单是引擎模拟订单，不是券商确认。
    print('Verified: actual LEAN course result and acceptance checks')


# 直接运行本文件才进入 main；作为模块导入以检查 prepare 时不会自动启动 Docker。
if __name__ == '__main__':
    # 开始上述准备、启动和结果检查流程。
    main()

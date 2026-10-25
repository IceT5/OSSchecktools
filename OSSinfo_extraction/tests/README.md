# 测试用例说明

本目录存放OSSinfo_extraction工具的完整测试套件。社区版本因工具源码
会部署到生产环境而不存放测试用例，本仓库作为源头仓库承担完整的测试
职责；向社区同步代码时不同步本目录。

## 测试体系

分为三层，自下而上：

| 层级 | 依赖 | 耗时 | 文件 |
|---|---|---|---|
| L1 单元层 | 无（构造ScanCode结果dict，确定性） | 秒级 | test_is_license_file / test_license_selection / test_normalize_license_path / test_copyright_extraction / test_readme_output / test_license_report / test_scancode / test_cleanup |
| L2 真实扫描 | PATH上的scancode + extractcode | 分钟级 | test_e2e_real_package（提取断言类） |
| L3 CLI行为 | 子进程完整流水线 | 分钟级 | test_e2e_real_package（参数与错误路径类） |

运行方式（仓库根目录执行）：

```bash
python -m pytest OSSinfo_extraction/tests -q                     # 全量（十余分钟，扫描用例为主）
python -m pytest OSSinfo_extraction/tests -q --ignore=OSSinfo_extraction/tests/test_e2e_real_package.py   # 仅单元层（秒级）
python -m pytest OSSinfo_extraction/tests/test_e2e_real_package.py -q   # 仅端到端
```

环境要求与自动跳过：

- 端到端用例依赖PATH上的`scancode`与`extractcode`，缺失时自动跳过
- 端到端断言编码了ScanCode **32.5.0**的检出行为：PATH上存在其他版本时，
  **仅扫描类用例**自动跳过（单元层与无需扫描的CLI用例不受影响）
- symlink相关用例在无创建权限的平台（未开启开发者模式的Windows）自动跳过
- 子进程固定`PYTHONUTF8`与`LOG_LEVEL=INFO`，不受运行环境影响

## 合成真实软件包（package_builder.py）

测试不依赖任何真实开源项目，由构造器生成虚构但高度仿真的发行包
`samplelib-1.2.3`：license全文取自ScanCode licensedcode数据
（`data/licenses/`，已剥离元数据头），保证扫描引擎真实检出对应SPDX标识。

包内布局覆盖真实世界的常见形态：

```
samplelib-1.2.3/
├── LICENSE                      # 根目录标准license（MIT全文）
├── LICENSES/                    # 一级LICENSES目录（宽松接受任意命名）
│   ├── Apache-2.0.txt
│   ├── GPL-3.0-only.txt
│   └── custom-exception.md      # 非license内容，检出为空不进报告
├── docs/LICENSE                 # 嵌套同名（BSD全文，遮蔽场景源）
├── third_party/tinylib/LICENSE  # 深层嵌套同名（Apache全文）
├── src/*.c|*.h                  # 四种版权书写形式：Copyright (c)/(c)/copr./Copyright (C)
├── NOTICE                       # 非license命名（模式不命中）
├── COPYING.LESSER               # LGPL-2.1全文
└── README.md、setup.py
```

变体与压缩格式：

- 目录形态（扁平/含顶层单目录）、zip/tar/tar.gz/tgz/tar.bz2/tbz2六种压缩格式
- 无顶层目录包（扁平）、双层wrapper嵌套包
- `shadow_order`变体：docs/LICENSE条目先于根LICENSE写入，复现扫描记录
  顺序敏感的遮蔽场景（#384）
- 英式拼写`LICENCE`包（tqdm场景）、SPDX版本后缀文件名包、无license包、近空包

## 场景覆盖矩阵

### 输入形态
- 目录输入、扁平压缩包（无顶层目录）、标准sdist嵌套、双层wrapper嵌套
- 六种压缩格式、近空包（仅占位文件）、不存在的target、非压缩包普通文件
- 嵌套压缩包（tar.gz内封装zip）：流水线以`--shallow`解压，内层压缩包
  不被递归解开，scancode不透视zip二进制，内层license不提取（固化边界）
- 损坏zip（extractcode不产出解压目录，流水线以"Expected extract
  directory not found"明确失败退出）
- 空zip（0条目，完整走通输出占位文案）
- 中文目录/文件名包（嵌套检测深入中文目录，正常提取中文版权声明）
- 文件名与内容不一致（LICENSE文件名装Apache全文，提取以内容为准）
- CRLF行尾、UTF-8 BOM的license文件正常检出；0字节license文件兜底
- 无license文件、仅源码内SPDX声明行的包：不进自动提取（工具以
  license文件为提取对象，固化现状边界）

### license文件名判定
- 标准命名与大小写、COPYING/COPYRIGHT系列、MIT/Apache等SPDX风格命名
- 英式拼写LICENCE系列
- SPDX版本后缀：`Apache-2.0`(.0)、`GPL-3.0-only`(.0-only)、`GPL-3.0-or-later`、
  `LPPL-1.3c`(.3c)、`Apache-2.0-with-exceptions`
- 精确关键词豁免（stem为LICENSE等关键词时跳过扩展名检查，如LICENSE.bak）
- 拒绝类：非license文件、`unlicence`（un前缀不因licence模式误收）、
  `licences.h`、`LICENSE2`、`my-license.txt`
- 合法特例：UNLICENSE/unlicense.txt有专门模式

### license位置与选择
- 根目录、LICENSES目录（含任意命名）、嵌套子目录
- 嵌套同名遮蔽：docs/、LICENSES/、third_party/*/LICENSE均不遮蔽根文件，
  且与扫描记录顺序无关（精确匹配语义）
- 显式子路径仍可选中嵌套文件（-p docs/LICENSE）
- 全量提取路径优先级：根目录 > LICENSES目录 > 其他（其他目录不自动提取）
- 同SPDX多位置去重；同SPDX不同表达式（带例外条款）各自保留

### -p参数与路径校验
- 正常解析返回(相对路径,绝对路径)元组；前导斜杠、Windows反斜杠、./相对形式
- 拒绝类（exit 1）：不存在、目录、../上跳（含docs/../../混合）、外部绝对路径、
  目标内symlink指向外部（resolve展开后越界）
- 接受类：..绕回目标内（docs/../LICENSE）、目标内symlink指向目标内文件
- -extract包装前缀还原：仅历史两层前缀形态（首段非扫描根名）剥离包装层；
  首段与扫描根名一致（含扁平压缩包的解压根名）时不剥，深度语义统一为
  首段=项目根名
- 用户意志优先（不受自动识别规则约束）：文件名不符合license模式（NOTICE）、
  二级LICENSES目录、任意命名但含检出的文件，显式-p一律选中；对照断言
  未指定-p时上述位置不进入自动提取
- 输入容错：尾部斜杠（LICENSE/）、多余前导斜杠（//LICENSE）、
  路径内连续斜杠（LICENSES//x.txt）均正常命中

### -l参数与组合
- 精确/部分/大小写不敏感匹配；无匹配时以用户名称兜底
- 限定符变体互包含：-l GPL-3.0-only与检出GPL-3.0（或反之）
- -l空串与未提供等价，降级为全量提取
- -l单独使用的端到端选中
- -l+-p一致性校验：匹配输出检出记录；不匹配时保留用户名+实际检出文本
- 路径无有效检出时回退Unknown记录（后续从磁盘读全文）

### 输出与其他
- 同一输出目录重复运行幂等（结果逐字节一致）
- -t相对路径（基于工作目录解析）

### 版权声明提取
- 四种书写形式全保留：Copyright (c)/(c)/copr./Copyright (C)
  （引擎将(C)归一化输出为(c)）
- statement字段回退；copyright字段优先于statement
- 空值/纯空白过滤；去重保持首次出现顺序
- 文档类后缀全集跳过（.md/.rst/.txt/.adoc/.markdown，含大写）

### 输出产物
- Readme.opensource逐段格式（Software头/Copyright Notice(s)/License段）
- license全文定位读取（含根名前缀剥离、唯一子目录回退）
- matched_text回退；无匹配时占位文案；无结尾换行补齐
- 非UTF-8编码文件按errors=replace容错
- license报告：段落格式、matched_text超500字符截断、空记录占位
- -o输出目录多级自动创建；默认输出到target同级；失败清理回调删除旧产物

### CLI行为
- --guide、缺必填参数（exit 2）、LOG_LEVEL=QUIET
- -j/--max-in-memory透传（命令组装契约与真实透传两层验证）

### 容错与安全护栏
- 扫描非零退出但有部分有效结果时告警续跑；无部分结果时RuntimeError
- 异常记录容错：缺path、缺license_detections、matches为空列表
- 短文本引用（无.LICENSE规则且matched_length<20）过滤；长度>=20有效
- headers为空列表/缺失时安全降级
- cleanup_extract_dir四分支：不存在跳过、非目录跳过、
  目录名不以-extract结尾拒绝删除（防误删安全栏）、删除失败仅告警

## 边界与极端场景清单

- 扁平压缩包（无顶层目录）：扫描记录的-extract前缀剥离后深度为1
- 遮蔽场景的顺序反转不变性
- unlicence/UNLICENCE不因英式拼写模式误收
- 空files列表、空license_detections、0字节占位包
- Latin-1编码license文件
- 重复zip条目防护（构造器保证同名条目唯一）
- scancode版本漂移门控、无scancode环境、无symlink权限平台
- CLI失败后*-extract残留目录的用例间隔离

## 已知行为说明（设计取舍，非缺陷）

- 扁平压缩包形态下，子目录license（如docs/LICENSE）的包装段会被剥离，
  剥离后深度为2按既有规则接受——与嵌套形态（深度3拒绝）存在差异；
  多收优于漏收，为既有行为
- 扁平形态下根文件与子目录文件同SPDX竞争时，两者清理后深度均为2、
  优先级同为1，选中取决于扫描记录顺序（规范嵌套包无此问题：子目录
  深度>=3被拒或排序靠后）
- ScanCode对LGPL等含交叉引用的全文检出复合表达式（如
  `LGPL-2.1-only AND ...`），端到端断言采用子串匹配而非整行精确匹配
- 版权声明按ScanCode原样保留，工具不做关键字二次过滤
  （有效声明可能是(c)/copr.形式，无copyright单词）

## 测试驱动修复的缺陷记录

1. 扁平压缩包（无顶层目录）根目录license被静默丢弃。根因是
   _clean_scancode_path的包装层剥离未区分“extract包装目录”与
   “extract目录本身即项目根”：扁平包的解压根就是项目根，扫描记录
   首段（恒为扫描根目录名）恰含-extract后缀被误剥，产生语义残缺的
   深度1路径落入防御分支被拒。修复：剥离增加结构判断——-extract段
   之后仍存在“目录/文件”两级结构才认定为包装层剥离；其后仅剩单个
   文件说明该-extract段就是项目根，保留不剥（记录与规范包的
   pkg-1.0/LICENSE同构，深度2走既有根文件逻辑）。深度1的两个防御
   分支与优先级映射保持原样——修正清理规则后深度1不再出现。
2. 扫描结果headers为空列表时license提取崩溃
   （修复：headers与input取值改为空安全）

## 新增用例约定

- 期望值以被测实现的**实际行为**为准（可先运行探针确认），不凭直觉写断言
- 端到端断言不得依赖扫描记录顺序；对检出表达式使用子串/宽松匹配
- 构造扫描数据的记录辅助函数见test_license_selection.py的`rec()`
- 需要真实扫描的用例必须打`@needs_scancode`标记

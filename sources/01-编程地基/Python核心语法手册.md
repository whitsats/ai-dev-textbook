# Python语法手册-核心内容

> **素材来源**：`raw/pdf/Python语法手册-核心内容.pdf`
> **页数**：238（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 211,449 字符，其中汉字 54,421 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

一，Python学习笔记
1- Python基础内容
1. 基本概念
解释型语言：Python 是一种解释型语言，代码运行时逐行解释执行。
动态类型：变量在运行时决定类型，无需声明。
2. 编码
定义：编码是将字符集转换为字节的方式。Python 3 默认使用 UTF-8 编码，能够支持多种语言的
字符。
文件编码声明
：在文件顶部可以声明编码格式，尽管在Python 3中通常不需要，因为它默认是UTF-8，但为了兼
容性，可以添加：
示例
：在字符串中使用中文字符。
注释：
块注释：
以#开始，一直到本行结束都是注释
为了保证代码的可读性，后面建议先添加一个空格，然后再编写相应的说明文字 （PEP8）
行内注释：
# 与代码同行,#前面至少有两个空格 （PEP8）
多行注释：
用一对 连续的 三个 引号(单引号和双引号都可以)
print()函数：
# -*- coding: utf-8 -*-
message = "你好，世界"
print(message)

---

<!-- p.2 -->

3. 标识符
定义：标识符用于命名变量、函数、类、模块等。
规则：
只能使用字母（A-Z、a-z）、数字（0-9）和下划线（_）。
不能以数字开头。
区分大小写（例如， myVar 和 myvar 是不同的）。
不能使用Python保留字（如 if , else , for , class 等）。
示例：
4. 变量命名
规则：遵循标识符的规则。
命名规范：
使用有意义的名称，以便代码可读。
对于变量名使用小写字母，多个单词用下划线分隔（如 total_sum ）。
类名通常使用驼峰命名法（如 MyClass ）。
常量（不变的值）通常使用全大写字母（如 MAX_SIZE ）。
示例：
5. 缩进
重要性：在Python中，缩进用于表示代码块，这意味着代码的结构依赖于缩进而非符号。
规则：
通常使用4个空格作为缩进，不建议混用空格和制表符。
在同一个代码块中，缩进量必须保持一致。
示例：
print(*objects, sep=' ', end='\n', file=None, flush=False)
sep:设置多个内容之间的分隔符
end:设置结束符，默认结束符\n
格式化输出：
%s:字符串
%d：有符号十进制整数，%06d表示的整数显示位数，不足的地方使用0补齐
%f：浮点数，%.2f表示小数点后只显示两位
%%：输出%
格式化输出格式：
print("格式化字符串" % (变量1, 变量2...))
my_variable = 10 # 合法
myVariable = 20 # 合法
1st_variable = 30 # 不合法，不能以数字开头
age = 25 # 合法变量
max_students = 30 # 合法变量名
class Student: # 合法类名
pass

---

<!-- p.3 -->

6. 注释
单行注释：使用 # 开头。
多行注释：使用三个引号（ ''' 或 """ ）。
7. 数据类型
基本数据类型：
整数（int）
浮点数（float）
字符串（str）
布尔值（bool）
复合数据类型：
列表（list）
元组（tuple）
字典（dict）
集合（set）
8. 变量
赋值操作：
9. 运算符
算术运算符：
加（ + ），减（ - ），乘（ * ），除（ / ），整除（ // ），取余（ % ），幂（ ** ）
比较运算符：
等于（ == ），不等于（ != ），大于（ > ），小于（ < ），大于等于（ >= ），小于等于
（ <= ）
逻辑运算符：
与（ and ），或（ or ），非（ not ）
if condition:
# 这个代码块缩进
do_something()
if another_condition:
do_something_else() # 进一步缩进
# 这是一个单行注释
'''
这是一个多行注释
可以用于注释多行代码
'''
x = 5
name = "Alice"

---

<!-- p.4 -->

10. 控制结构
条件语句：
循环语句：
for 循环：
while 循环：
11. 函数
定义函数：
调用函数：
12. 模块与包
导入模块：
13. 异常处理
使用 try 和 except 处理异常：
if condition:
# 执行代码块
elif another_condition:
# 执行其他代码块
else:
# 执行备用代码块
for i in range(5):
print(i)
while condition:
# 执行代码块
def function_name(parameters):
# 函数体
return value
result = function_name(arguments)
import module_name
from module_name import function_name
try:
# 可能会出错的代码
except SomeException:
# 处理错误的代码

---

<!-- p.5 -->

14. 文件操作
打开文件：
15. 列表、元组、字典、集合的基本操作
列表：
元组：
字典：
集合：
16. 列表推导式
简洁的创建列表：
17. Lambda 函数
匿名函数：
18. 类与对象
定义类：
with open('filename.txt', 'r') as file:
content = file.read()
my_list = [1, 2, 3]
my_list.append(4) # 添加元素
my_tuple = (1, 2, 3) # 不可变
my_dict = {'key': 'value'}
my_dict['new_key'] = 'new_value' # 添加键值对
my_set = {1, 2, 3}
my_set.add(4) # 添加元素
squares = [x**2 for x in range(10)]
add = lambda x, y: x + y
class MyClass:
def __init__(self, value):
self.value = value
def display(self):
print(self.value)

---

<!-- p.6 -->

创建对象：
19. 常用内置函数
len() ：获取长度
type() ：获取类型
print() ：输出
input() ：输入
2- 标识符
1. 标识符的定义
1.1 定义
标识符是用于命名变量、函数、类、模块、包等的名称。它们在程序中用于唯一标识这些元素，方便程
序员进行引用和操作。
2. 标识符的规则
2.1 字符组成
标识符可以包含字母（A-Z、a-z）、数字（0-9）和下划线（_）。
标识符的第一个字符不能是数字。
2.2 长度限制
标识符的长度没有固定限制，但应该保持简短且有意义。
2.3 大小写敏感
Python 区分大小写，因此 myVariable 和 myvariable 是两个不同的标识符。
2.4 不能使用保留字
Python 有一组保留字（关键字），这些词在语言中有特定的含义，不能用作标识符。常见的保留
字包括 if , for , while , class , def , return 等。
3. 标识符的命名规范
3.1 意义明确
选择能够反映变量用途的名称，例如 count 、 user_name 等。
3.2 使用小写字母
常规变量使用小写字母，多个单词之间用下划线分隔（如 total_price ）。
obj = MyClass(10)
obj.display()

---

<!-- p.7 -->

3.3 类名使用驼峰命名法
类名通常采用首字母大写的驼峰命名法（如 StudentRecord ）。
3.4 常量全大写
常量（不变的值）通常使用全大写字母，单词之间用下划线分隔（如 MAX_SIZE ）。
3.5 避免使用单字符命名
除非在循环或临时变量中，尽量避免使用单字符名称（如 x , y ），应尽量使用更具描述性的名
称。
4. 示例
好的，下面为 4.1 合法标识符 和 4.2 非法标识符 添加更多示例。
4.1 合法标识符
4.2 非法标识符
5. 常见错误
5.1 使用保留字
确保没有使用Python的保留字作为标识符。
user_name = "Alice" # 小写字母和下划线
age = 30 # 字母和数字
MAX_SIZE = 100 # 常量，使用全大写
MyClass = "class_name" # 类名，使用驼峰命名法
total_price = 250.75 # 有意义的名称，描述了变量用途
is_valid = True # 布尔值变量，以 is 开头
student_count = 45 # 有描述性的变量名，使用下划线分隔
_user = "hidden" # 以下划线开头的变量名，常用于内部变量
PI = 3.14159 # 常量，用全大写字母表示
EmployeeID = "E12345" # 类名或特定变量的驼峰命名法
first_name = "John" # 多个单词用下划线分隔
x = 10 # 虽然单字符命名，但在某些情况下合法，例如循环变量
1st_variable = 10 # 不合法，不能以数字开头
my-variable = 20 # 不合法，使用了非法字符（-）
class = "test" # 不合法，使用了保留字
@username = "admin" # 不合法，使用了非法字符（@）
def = "function" # 不合法，使用了保留字
first name = "Alice" # 不合法，包含空格
$salary = 5000 # 不合法，使用了非法字符（$）
3d_model = "model1" # 不合法，数字不能在开头
global = "global_var" # 不合法，使用了保留字
if_ = "condition" # 不建议使用，虽然 `if_` 合法，但容易混淆

---

<!-- p.8 -->

5.2 字符限制
确保标识符不以数字开头，并且不使用特殊字符（如 @ , # , - , ! ）。
5.3 大小写问题
注意标识符的大小写，确保在引用时保持一致。
3- 变量命名
1. 变量命名的基本规则
在 Python 中，变量名必须遵循以下规则：
1. 只能包含字母、数字和下划线，并且不能以数字开头。
示例：合法的变量名有 name , age23 , school_name 等。
不合法的变量名有 1name , school-name 等。
2. 区分大小写。
age 和 Age 是两个不同的变量。
3. 不能使用 Python 的保留字，如 if , for , while , class 等。
示例： for 不能作为变量名，但可以用 for_ 代替。
4. 变量名应简洁且具有描述性，使代码更易读和维护。
2. 常用命名规范
2.1 使用下划线分隔单词（snake_case）
在 Python 中，通常采用小写字母和下划线分隔的方式（ snake_case ），这是一种广泛使用的变量命
名方式。
示例：
2.2 使用全大写表示常量
通常在代码中，我们用全大写字母表示常量（不变的值）。常量名称中间用下划线分隔，这样的命名便
于一眼看出该变量不应被修改。
示例：
3. 一些举例
根据你的个人信息，以下是一些合理的变量命名示例：
user_name = "aini" # 使用小写字母和下划线分隔单词
age = 23 # 简单的变量名
university = "东华大学" # 简洁的描述性名称
city = "上海" # 描述性强的变量
MAX_AGE = 100 # 假设这是某个最大年龄限制
BIRTH_YEAR = 2000 # 假设你的出生年份

---

<!-- p.9 -->

4. 常见变量命名的类别与规范
4.1 布尔值命名
布尔值（ True 或 False ）的变量通常用 is_ 或 has_ 开头，表示状态或特性。
示例：
4.2 列表和集合的命名
如果一个变量存储多个值（如兴趣爱好、已修课程等），可以用复数形式或 _list 结尾。
示例：
4.3 使用描述性强的名字
变量命名时，尽量选择能够反映变量内容的名字，不要过于简短或模糊。比如， name 可以更明确为
user_name 或 student_name 。
示例：
5. 不推荐的命名方式
1. 使用无意义的单字符变量名（除非在循环中，通常我们避免使用单字符变量名）。
如 a = 23 ， n = "东华大学" ，这种命名方式信息不明确。
2. 混用大小写（除非明确需要区分大小写），过多的大小写会影响可读性。
如 MyName = "aini" ， AGE23 = 23 ，不推荐在普通变量中使用驼峰或全大写，容易误解。
3. 模糊的缩写，除非缩写很常用，否则避免使用不直观的缩写。
如 usr = "aini" 可能代表用户（user），但最好用 user_name 这样更清晰。
# 基本个人信息
name = "aini" # 存储名字
age = 23 # 存储年龄
university_name = "东华大学" # 存储大学名称
city_of_residence = "上海" # 存储居住城市
# 更详细的信息（扩展为描述性变量）
birth_year = 2000 # 假设你的出生年份
hobby_list = ["阅读", "运动"] # 兴趣爱好，可以用列表形式
is_student = True # 布尔变量，表示是否为学生
graduation_year = 2025 # 假设毕业年份
is_student = True # 表示是否是学生
has_scholarship = False # 表示是否有奖学金
is_graduated = False # 表示是否已毕业
hobbies = ["阅读", "运动"] # 兴趣爱好
completed_courses = ["数学", "物理"] # 已修课程
friend_names = ["李明", "王芳"] # 朋友的名字
user_name = "aini" # 用户名
current_city = "上海" # 当前居住城市
enrolled_university = "东华大学" # 所在大学

---

<!-- p.10 -->

6. 结合示例的完整代码
综合以上命名规则，以下是一段 Python 代码示例：
4- 缩进和注释
1. 缩进
1.1 缩进的定义和作用
在 Python 中，缩进用于标识代码块。与许多编程语言不同，Python 没有用 {} 来包裹代码块，而是依
靠缩进来确定层次结构。因此，缩进在 Python 中是强制的，它不仅用于代码的可读性，还决定了代码
的执行结构。
1.2 缩进的基本规则
1. 缩进一致性：在同一个代码块中，所有缩进必须保持一致。Python 的默认缩进规范是 4 个空格，
也可以用一个 Tab 键，但不能混合使用。
2. 代码块结构：Python 通过缩进来识别不同的代码块。例如，在 if 、 for 、 while 等语句后面缩
进的部分被认为是属于这些语句的代码块。
1.3 缩进示例
以 if 语句为例，来看一下如何使用缩进来定义代码块：
在上面的代码中， if 和 else 语句下面的代码都缩进了 4 个空格，这表示这些缩进的代码是属于各自
条件的代码块。
# 基本信息
user_name = "aini" # 用户名
age = 23 # 年龄
university_name = "东华大学" # 大学名称
city_of_residence = "上海" # 居住城市
birth_year = 2000 # 出生年份
is_student = True # 是否为学生
graduation_year = 2025 # 预计毕业年份
# 扩展信息
hobby_list = ["阅读", "运动"] # 兴趣爱好
has_scholarship = False # 是否有奖学金
completed_courses = ["数学", "物理"] # 已修课程
friend_names = ["李明", "王芳"] # 朋友名字列表
age = 23
if age >= 18:
print("你已成年") # 这个缩进属于 if 语句的代码块
print("可以参与投票") # 这个也是 if 语句的代码块
else:
print("你未成年") # 这个属于 else 语句的代码块

---

<!-- p.11 -->

1.4 缩进错误示例
如果缩进不一致或不符合 Python 规范，就会导致 IndentationError 错误。
在这个例子中，第二行和第三行的缩进不一致（一个是 4 个空格，另一个是 5 个空格），Python 会报
错。
1.5 嵌套缩进
当代码块有多层嵌套时，每一层嵌套都需要再缩进一次，通常每一层使用 4 个空格。
在这个例子中， if 语句中的嵌套 if 和 else 语句都进一步缩进了 4 个空格。
2. 注释
注释是对代码的解释说明，用于帮助开发者理解代码的作用和逻辑。Python 支持单行注释和多行注释。
2.1 单行注释
在 Python 中，单行注释使用 # 符号。 # 后的内容不会被 Python 解释器执行，通常用于解释代码行的
功能。
用法： # 后面可以跟任何注释内容。通常单行注释会放在代码上方或者旁边。
示例：
多行单行注释：如果需要多行注释，但每行只有简单的注释内容，可以在每行前面加 # 。
if age >= 18:
print("你已成年")
print("可以参与投票") # 不一致的缩进，将导致 IndentationError
age = 23
is_student = True
if age >= 18:
print("你已成年")
if is_student:
print("你是成年学生") # 进一步嵌套的代码块，每层缩进 4 个空格
else:
print("你不是学生")
else:
print("你未成年")
age = 23 # 定义年龄变量，值为23
# 这是一个多行注释
# 说明这段代码的作用
# 以及每行的功能

---

<!-- p.12 -->

2.2 多行注释
多行注释在 Python 中通常使用三个单引号 ''' 或三个双引号 """ 括起来的内容。这种方式的注释主
要用于函数或类的文档字符串（docstring），也可以用于多行注释，但在一般代码中单行注释更为常
见。
用法：在代码块前或后使用 '''注释内容''' 或 """注释内容""" 包裹多行注释。
示例：
2.3 函数和类的文档字符串（docstring）
当编写函数、类或模块时，建议在定义的第一行使用多行注释来描述它的功能。这样可以为函数或类提
供文档说明，方便其他人了解它的用途。
函数文档字符串示例：
类文档字符串示例：
2.4 注释的规范与最佳实践
注释要简洁明了：注释应该清楚明白地解释代码的意图，而不是重复代码本身。例如，以下注释是
多余的：
可以改为：
注释重要逻辑或复杂代码：对于重要的代码逻辑和复杂的部分，应提供详细的解释。
避免过多注释：不要在每一行都添加注释，过多的注释会影响可读性。只在关键地方添加注释即
可。
'''
这是一个多行注释
可以用来描述整个函数的作用
或者解释代码逻辑
'''
def greet_user(name):
"""打印问候用户的消息"""
print(f"你好, {name}")
class Student:
"""这是一个学生类，用于存储学生的基本信息"""
def __init__(self, name, age):
"""初始化学生的名字和年龄"""
self.name = name
self.age = age
count = 0 # 将计数变量设置为0
count = 0 # 记录用户的数量

---

<!-- p.13 -->

3. 结合缩进和注释的代码示例
结合缩进和注释，以下是一个示例代码，展示了如何使用合理的缩进和注释来编写清晰、易读的 Python
代码：
在这个示例中：
缩进：代码中使用 4 个空格来缩进每个代码块，保持一致性。
注释：代码中的每个逻辑步骤都配有简洁明了的注释，文档字符串则详细说明了函数的用途和参
数。
5- 数据类型
1. 基本数据类型
Python 的基本数据类型包括整数（int）、浮点数（float）、布尔值（bool）、字符串（str）等。
1.1 整数（int）
定义：整数是没有小数部分的数，可以是正数、负数或零。
表示：Python 中的整数可以表示任意大小，因为 Python 会根据需要自动扩展整数的存储空间。
示例：
def check_eligibility(age, city):
"""
检查用户的资格，根据年龄和所在城市决定是否符合条件
参数:
age (int): 用户的年龄
city (str): 用户所在的城市
返回:
bool: 如果符合资格返回 True，否则返回 False
"""
# 判断年龄是否大于等于18
if age >= 18:
# 如果年龄合格，继续检查城市
if city == "上海":
return True # 满足条件，返回 True
else:
return False # 城市不符合条件，返回 False
else:
return False # 年龄不符合条件，返回 False
# 调用函数并打印结果
user_age = 23
user_city = "上海"
is_eligible = check_eligibility(user_age, user_city) # 检查用户是否符合资格
print(is_eligible) # 打印结果

---

<!-- p.14 -->

常用操作：
加法： a + b
减法： a - b
乘法： a * b
整除： a // b （返回商的整数部分）
取余： a % b （返回除法的余数）
幂运算： a ** b （a 的 b 次幂）
小整数的地址问题：
1.2 浮点数（float）
定义：浮点数是带小数部分的数字，通常用于表示小数或科学计数法形式的数。
精度问题：由于计算机内部的存储机制，浮点数的精度有限，可能出现误差。
示例：
常用操作：与整数的操作相同，不过浮点数除法结果为浮点数。
1.3 布尔值（bool）
定义：布尔值只有 True 和 False 两个值，通常用于逻辑判断。
表达式：布尔值通常通过条件表达式得到，如 a > b 、 a == b 等。
示例：
常用操作：
与（and）： True and False 返回 False
或（or）： True or False 返回 True
非（not）： not True 返回 False
age = 23 # 整数
temperature = -5 # 负整数
big_number = 1000000 # 大整数
Python中的小整数，通常指的是-5至256之间的整数。
当你在Python中创建一个整数对象时，Python会根据该整数的值动态地为其分配内存空间。对于小整数，
Python会使用一种称为“小整数缓存”的机制来优化内存使用。这个缓存池中的整数对象会被重复利用，而不
是为每个新创建的小整数分配新的内存空间。这样可以减少内存分配和释放的开销，提高程序的性能。
如果你需要跟踪Python对象的内存地址，可以使用Python提供的内置函数id()来获取对象的唯一标识符，这
个标识符通常可以用来近似地表示对象的内存地址。但是请注意，这个标识符并不是真正的内存地址，而是由
Python解释器生成的一个唯一标识符，用于区分不同的对象实例。
price = 19.99 # 小数
pi = 3.14159 # 常见的浮点数
scientific_notation = 1.23e4 # 科学计数法表示，等价于 1.23 * 10^4
is_student = True # 表示是否为学生
has_scholarship = False # 表示是否有奖学金

---

<!-- p.15 -->

1.4 字符串（str）
定义：字符串是由字符组成的序列，通常用于表示文本信息。
表示：可以使用单引号（ ' ）、双引号（ " ）或三重引号（ ''' 或 """ ）定义。
示例：
常用操作：
字符串拼接： "Hello" + " World" -> "Hello World"
重复： "Hi" * 3 -> "HiHiHi"
取子串： "Hello"[1:4] -> "ell"
常用方法： len("Hello") 、 "hello".upper() 、 "WORLD".lower() 、 "Hello
World".split() 。
2. 复合数据类型
复合数据类型包括列表（list）、元组（tuple）、字典（dict）和集合（set）。它们可以用来存储多个
值，方便处理复杂的数据结构。
2.1 列表（list）
定义：列表是一个有序的可变序列，可以存储多个元素，元素之间用逗号分隔。
表示：列表使用方括号 [] 表示。
示例：
常用操作：
访问元素： hobbies[0] -> "阅读"
修改元素： hobbies[1] = "跑步"
添加元素： hobbies.append("电影")
删除元素： hobbies.remove("运动")
列表切片： numbers[1:3] -> [2, 3]
2.2 元组（tuple）
定义：元组是一个有序的不可变序列，一旦定义无法修改，通常用于存储不会改变的数据。
表示：元组使用小括号 () 表示。
示例：
name = "aini" # 使用双引号
greeting = 'Hello' # 使用单引号
long_text = """这是一个多行字符串
可以换行显示"""
hobbies = ["阅读", "运动", "音乐"] # 定义一个包含多个元素的列表
numbers = [1, 2, 3, 4, 5] # 定义一个数字列表
mixed_list = ["aini", 23, True] # 可以包含不同类型的元素
coordinates = (30.0, 50.0) # 定义一个坐标元组
personal_info = ("aini", 23, "上海") # 存储不可变的个人信息
single_item_tuple = (42,) # 包含一个元素的元组，后面需加逗号

---

<!-- p.16 -->

常用操作：
访问元素： coordinates[0] -> 30.0
元组解包： x, y = coordinates -> x = 30.0, y = 50.0
2.3 字典（dict）
定义：字典是一个无序的键值对集合，使用键（key）来访问对应的值（value），键必须是唯一
的。
表示：字典使用大括号 {} 表示，每个键值对用冒号 : 分隔。
示例：
常用操作：
访问值： student_info["name"] -> "aini"
修改值： student_info["age"] = 24
添加键值对： student_info["major"] = "计算机科学"
删除键值对： del student_info["city"]
获取键集合： student_info.keys()
获取值集合： student_info.values()
2.4 集合（set）
定义：集合是一个无序、唯一的元素集合，主要用于去重和集合运算。
表示：集合使用大括号 {} 表示，元素之间用逗号分隔，或使用 set() 函数创建空集合。
示例：
常用操作：
添加元素： unique_numbers.add(6)
删除元素： unique_numbers.remove(2)
并集： set1 | set2
交集： set1 & set2
差集： set1 - set2
对称差集： set1 ^ set2
3. 特殊数据类型：NoneType
定义： NoneType 是一个特殊的空值类型，只有一个值 None ，用于表示“什么都没有”。
用途： None 常用于表示缺失值、空返回值等。
示例：
student_info = {
"name": "aini",
"age": 23,
"city": "上海",
"university": "东华大学"
}
unique_numbers = {1, 2, 3, 4, 5, 5} # 集合会自动去重
empty_set = set() # 使用 set() 创建空集合

---

<!-- p.17 -->

6- 运算符
6.1 算术运算符（掌握）
算术运算符用于进行数学计算，包括加、减、乘、除等基本操作。它们是编程中最常用的运算符。
运算符 描述 示例 结果
+ 加法 3 + 2 5
- 减法 3 - 2 1
* 乘法 3 * 2 6
/ 除法 3 / 2 1.5
// 整除 3 // 2 1
% 取余 3 % 2 1
** 幂运算 3 ** 2 9
常见的算术运算符：
示例代码：
6.2 比较运算符（掌握）
比较运算符用于比较两个值，结果返回布尔值 True 或 False ，在条件判断中非常常用。
常见的比较运算符：
result = None # 初始值为 None，表示还没有结果
a = 10
b = 3
print(a + b) # 输出 13
print(a - b) # 输出 7
print(a * b) # 输出 30
print(a / b) # 输出 3.3333333333333335
print(a // b) # 输出 3
print(a % b) # 输出 1
print(a ** b) # 输出 1000

---

<!-- p.18 -->

运算符 描述 示例 结果
== 等于 3 == 2 False
!= 不等于 3 != 2 True
> 大于 3 > 2 True
< 小于 3 < 2 False
>= 大于等于 3 >= 2 True
<= 小于等于 3 <= 2 False
示例代码：
6.3 赋值运算符（掌握）
赋值运算符用于将值赋给变量，并支持自加、自减、自乘等简便操作。是编程中非常基础且常用的运算
符。
运算符 描述 示例 等价于
= 赋值 x = 5 x = 5
+= 加赋值 x += 3 x = x + 3
-= 减赋值 x -= 3 x = x - 3
*= 乘赋值 x *= 3 x = x * 3
/= 除赋值 x /= 3 x = x / 3
//= 整除赋值 x //= 3 x = x // 3
%= 取余赋值 x %= 3 x = x % 3
**= 幂赋值 x **= 3 x = x ** 3
常见的赋值运算符：
示例代码：
x = 5
y = 10
print(x == y) # 输出 False
print(x != y) # 输出 True
print(x > y) # 输出 False
print(x < y) # 输出 True
print(x >= y) # 输出 False
print(x <= y) # 输出 True

---

<!-- p.19 -->

6.4 逻辑运算符（掌握）
逻辑运算符用于组合多个条件，返回布尔值 True 或 False ，在条件判断和控制结构中十分常用。
运算符 描述 示例 结果
and 逻辑与 True and False False
or 逻辑或 True or False True
not 逻辑非 not True False
常见的逻辑运算符：
示例代码：
6.5 位运算符（了解）
位运算符用于直接操作二进制位，主要用于底层编程或硬件控制，对一般的应用程序开发不常用。
运算符 描述 示例 结果
& 按位与 5 & 3 1
| 按位或 5 | 3 7
^ 按位异或 5 ^ 3 6
~ 按位取反 ~5 -6
<< 左移 5 << 1 10
>> 右移 5 >> 1 2
常见的位运算符：
示例代码：
x = 10
x += 5 # 等价于 x = x + 5，结果为 15
x -= 3 # 等价于 x = x - 3，结果为 12
x *= 2 # 等价于 x = x * 2，结果为 24
x /= 4 # 等价于 x = x / 4，结果为 6.0
a = True
b = False
print(a and b) # 输出 False
print(a or b) # 输出 True
print(not a) # 输出 False

---

<!-- p.20 -->

6.6 成员运算符（掌握）
成员运算符用于检查某个值是否存在于序列（如列表、元组、字符串）中，返回布尔值 True 或
False ，在数据结构操作中非常常用。
运算符 描述 示例 结果
in 在序列中 'a' in 'apple' True
not in 不在序列中 'b' not in 'apple' True
常见的成员运算符：
示例代码：
6.7 身份运算符（了解）
身份运算符用于比较两个对象的内存地址，判断它们是否是同一个对象。适合在需要比较对象身份的场
景中使用，常
用于对象的内存管理。
运算符 描述 示例 结果
is 是同一个对象 a is b True 或 False
is not 不是同一个对象 a is not b True 或 False
常见的身份运算符：
示例代码：
a = 5 # 二进制为 0101
b = 3 # 二进制为 0011
print(a & b) # 输出 1（二进制为 0001）
print(a | b) # 输出 7（二进制为 0111）
print(a ^ b) # 输出 6（二进制为 0110）
print(~a) # 输出 -6（二进制为 -0110，补码表示）
print(a << 1) # 输出 10（二进制为 1010）
print(a >> 1) # 输出 2（二进制为 0010）
fruits = ["apple", "banana", "cherry"]
print("apple" in fruits) # 输出 True
print("grape" not in fruits) # 输出 True
x = [1, 2, 3]
y = x
z = [1, 2, 3]
print(x is y) # 输出 True，因为 y 和 x 是同一个对象
print(x is z) # 输出 False，因为 z 是另一个列表，虽然内容相同
print(x == z) # 输出 True，因为 x 和 z 的内容相同

---

<!-- p.21 -->

6.8 运算符优先级（掌握）
运算符优先级决定了运算符的执行顺序，优先级高的运算符会先执行。在复合运算中，理解运算符优先
级可以帮助我们正确书写表达式。
运算符优先级（从高到低）：
1. 指数运算符： **
2. 按位取反、逻辑非： ~ , not
3. 乘除、取余、整除： * , / , // , %
4. 加减： + , -
5. 移位运算符： << , >>
6. 比较运算符： < , <= , > , >=
7. 等于运算符： == , !=
8. 位运算符： & , ^ , |
9. 逻辑运算符： and , or
10. 赋值运算符： = , += , -= , *= , /= , %= 等
万能方法：实在搞不清优先级，那就用()，希望先计算的用() 括起来
7- 字符串
7.1 字符串的定义（掌握）
字符串是一种由字符组成的不可变序列，用于表示文本数据。在 Python 中，字符串可以使用单引号
' 、双引号 " 或三引号 ''' / """ 来定义。
单引号和双引号：用于定义单行字符串，二者功能一致。
三引号：用于定义多行字符串，适合长文本或多行注释。
7.2 字符串的基本操作（掌握）
7.2.1 字符串拼接
使用 + 运算符将多个字符串拼接在一起。
name = 'aini'
greeting = "Hello"
long_text = """这是一个
多行字符串"""
first_name = "aini"
last_name = "Zhang"
full_name = first_name + " " + last_name # 输出 'aini Zhang'

---

<!-- p.22 -->

7.2.2 字符串重复
使用 * 运算符将字符串重复多次。
7.2.3 字符串长度
使用 len() 函数获取字符串的字符数。
7.2.4 字符串索引与切片
索引：使用索引访问字符串中的单个字符，索引从 0 开始，支持负索引。
切片：使用切片获取字符串中的部分内容，格式为 字符串[起始:结束:步长] 。
7.3 字符串的常用方法（掌握）
Python 提供了丰富的字符串方法，以下是常用的字符串方法，主要用于字符串的处理和格式化。
7.3.1 upper() 和 lower() ：转换大小写
upper() ：将字符串全部转换为大写。
lower() ：将字符串全部转换为小写。
7.3.2 strip() ：去除空白字符
strip() ：去除字符串两端的空白字符（包括空格、换行符等）。
lstrip() ：去除左侧空白字符。
rstrip() ：去除右侧空白字符。
repeated = "Hello" * 3 # 输出 'HelloHelloHello'
message = "Hello, World!"
print(len(message)) # 输出 13
text = "Python"
print(text[0]) # 输出 'P'
print(text[-1]) # 输出 'n'
text = "Python"
print(text[1:4]) # 输出 'yth'
print(text[:3]) # 输出 'Pyt'
print(text[::2]) # 输出 'Pto'
print(text[::-1]) # 输出 'nohtyP'（字符串反转）
text = "Hello World"
print(text.upper()) # 输出 'HELLO WORLD'
print(text.lower()) # 输出 'hello world'

---

<!-- p.23 -->

7.3.3 replace() ：替换子字符串
replace(old, new) ：将字符串中的 old 替换为 new 。
7.3.4 split() 和 join() ：拆分与合并字符串
split(separator) ：根据指定的分隔符将字符串拆分成列表。如果不指定分隔符，默认按空白字
符拆分。
join(iterable) ：将可迭代对象中的元素连接成一个字符串，以调用者作为分隔符。
7.3.5 find() 和 index() ：查找子字符串
find(sub) ：查找子字符串 sub 的位置，找到则返回索引，否则返回 -1。
index(sub) ：与 find 类似，但如果找不到会引发 ValueError 。
7.4 字符串格式化（掌握）
Python 提供了多种格式化字符串的方法，便于拼接变量和字符串。
7.4.1 f-string 格式化（Python 3.6 及以上）
使用 f"{变量}" 的方式嵌入变量，非常直观且易读。
text = " Hello World "
print(text.strip()) # 输出 'Hello World'
print(text.lstrip()) # 输出 'Hello World '
print(text.rstrip()) # 输出 ' Hello World'
text = "Hello World"
print(text.replace("World", "Python")) # 输出 'Hello Python'
text = "Hello World"
print(text.split()) # 输出 ['Hello', 'World']
print(text.split('o')) # 输出 ['Hell', ' W', 'rld']
words = ["Hello", "Python", "World"]
print(" ".join(words)) # 输出 'Hello Python World'
text = "Hello World"
print(text.find("World")) # 输出 6
print(text.index("World")) # 输出 6
name = "aini"
age = 23
message = f"Hello, my name is {name} and I am {age} years old."
print(message) # 输出 'Hello, my name is aini and I am 23 years old.'

---

<!-- p.24 -->

7.4.2 str.format() 方法
使用 {} 占位符，并在字符串末尾调用 .format() 方法填充变量。
7.4.3 百分号 % 格式化（旧方法）
使用 % 运算符来进行格式化，在旧代码中仍然常见。
7.5 字符串的编码与解码（了解）
编码与解码用于将字符串转换为字节或将字节转换为字符串。通常用于处理文件、网络传输和多语言文
本处理。
7.5.1 encode() ：编码字符串
encode(encoding) ：将字符串转换为指定编码格式的字节对象（ bytes ）。
7.5.2 decode() ：解码字节
decode(encoding) ：将字节对象转换回指定编码格式的字符串。
7.6 字符串的常见检查方法（掌握）
用于判断字符串是否符合特定格式或内容。
7.6.1 isalpha() ：检查是否全为字母
返回 True 如果字符串只包含字母且非空，否则返回 False 。
name = "aini"
age = 23
message = "Hello, my name is {} and I am {} years old.".format(name, age)
print(message) # 输出 'Hello, my name is aini and I am 23 years old.'
name = "aini"
age = 23
message = "Hello, my name is %s and I am %d years old." % (name, age)
print(message) # 输出 'Hello, my name is aini and I am 23 years old.'
text = "Hello"
byte_text = text.encode("utf-8")
print(byte_text) # 输出 b'Hello'
byte_text = b'Hello'
text = byte_text.decode("utf-8")
print(text) # 输出 'Hello'
text = "Hello"
print(text.isalpha()) # 输出 True

---

<!-- p.25 -->

7.6.2 isdigit() ：检查是否全为数字
返回 True 如果字符串只包含数字且非空，否则返回 False 。
7.6.3 isalnum() ：检查是否全为字母和数字
返回 True 如果字符串只包含字母和数字且非空，否则返回 False 。
7.6.4 isspace() ：检查是否全为空白字符
返回 True 如果字符串只包含空白字符（如空格、制表符）且非空，否则返回 False 。
8- 列表
8.1 列表的定义（掌握）
列表是一个有序的、可变的序列，可以包含任意类型的元素。列表是 Python 中最常用的数据结构之
一，适合存储一系列数据。列表用方括号 [] 表示，元素之间用逗号分隔。
定义列表：
8.2 列表的基本操作（掌握）
列表支持多种基本操作，如访问、修改、添加和删除元素。
8.2.1 访问元素
使用索引访问列表中的元素，索引从 0 开始，支持负索引。
text = "12345"
print(text.isdigit()) # 输出 True
text = "Hello123"
print(text.isalnum()) # 输出 True
text = " "
print(text.isspace()) # 输出 True
empty_list = [] # 空列表
numbers = [1, 2, 3, 4, 5] # 包含整数的列表
mixed_list = [1, "hello", 3.14, True] # 混合数据类型的列表
numbers = [1, 2, 3, 4, 5]
print(numbers[0]) # 输出 1
print(numbers[-1]) # 输出 5（最后一个元素）

---

<!-- p.26 -->

8.2.2 修改元素
使用索引修改列表中的元素。
8.2.3 列表切片
使用切片获取列表中的一部分，格式为 列表[起始:结束:步长] 。
8.2.4 列表长度
使用 len() 函数获取列表的长度。
8.3 列表的常用方法（掌握）
Python 提供了多种方法来操作列表，这些方法可以帮助我们对列表进行添加、删除、查找等操作。
8.3.1 append() ：添加元素到列表末尾
使用 append() 方法将元素添加到列表的末尾。
8.3.2 insert() ：在指定位置插入元素
使用 insert(index, element) 方法在指定位置插入元素。
8.3.3 extend() ：扩展列表
使用 extend() 方法将一个列表的所有元素添加到另一个列表末尾。
numbers = [1, 2, 3, 4, 5]
numbers[0] = 10
print(numbers) # 输出 [10, 2, 3, 4, 5]
numbers = [1, 2, 3, 4, 5]
print(numbers[1:4]) # 输出 [2, 3, 4]
print(numbers[:3]) # 输出 [1, 2, 3]
print(numbers[::2]) # 输出 [1, 3, 5]
print(numbers[::-1]) # 输出 [5, 4, 3, 2, 1]（列表反转）
numbers = [1, 2, 3, 4, 5]
print(len(numbers)) # 输出 5
numbers = [1, 2, 3]
numbers.append(4)
print(numbers) # 输出 [1, 2, 3, 4]
numbers = [1, 2, 3]
numbers.insert(1, "hello")
print(numbers) # 输出 [1, 'hello', 2, 3]

---

<!-- p.27 -->

8.3.4 remove() ：删除指定元素
使用 remove(element) 方法删除列表中的第一个匹配的元素。如果元素不存在，会引发
ValueError 。
8.3.5 pop() ：弹出指定位置的元素
使用 pop(index) 方法删除并返回指定位置的元素。如果不指定索引，默认删除并返回最后一个
元素。
8.3.6 clear() ：清空列表
使用 clear() 方法删除列表中的所有元素。
8.3.7 index() ：查找元素的索引
使用 index(element) 方法返回元素在列表中的第一个匹配索引。如果元素不存在，会引发
ValueError 。
8.3.8 count() ：统计元素出现次数
使用 count(element) 方法统计指定元素在列表中出现的次数。
numbers = [1, 2, 3]
more_numbers = [4, 5, 6]
numbers.extend(more_numbers)
print(numbers) # 输出 [1, 2, 3, 4, 5, 6]
numbers = [1, 2, 3, 2, 4]
numbers.remove(2)
print(numbers) # 输出 [1, 3, 2, 4]
numbers = [1, 2, 3, 4]
last_element = numbers.pop()
print(numbers) # 输出 [1, 2, 3]
print(last_element) # 输出 4
numbers = [1, 2, 3, 4]
numbers.clear()
print(numbers) # 输出 []
numbers = [1, 2, 3, 4]
print(numbers.index(3)) # 输出 2
numbers = [1, 2, 2, 3, 4]
print(numbers.count(2)) # 输出 2

---

<!-- p.28 -->

8.3.9 sort() 和 sorted() ：排序
使用 sort() 方法对列表进行原地排序，改变原列表。可以传入 reverse=True 参数降序排序。
使用 sorted() 函数返回一个排序后的新列表，不改变原列表。
8.3.10 reverse() ：反转列表
使用 reverse() 方法将列表中的元素顺序反转，改变原列表。
8.4 列表的生成式（掌握）
列表生成式（List Comprehension）是一种简洁的生成列表的方法，可以用一行代码创建一个新的列
表，常用于数据处理和过滤。
基本语法：
示例：
8.5 列表的嵌套（掌握）
列表可以包含其他列表，形成嵌套结构，用于表示二维或多维数据。
示例：
numbers = [3, 1, 4, 2]
numbers.sort()
print(numbers) # 输出 [1, 2, 3, 4]
numbers = [3, 1, 4, 2]
sorted_numbers = sorted(numbers, reverse=True)
print(sorted_numbers) # 输出 [4, 3, 2, 1]
numbers = [1, 2, 3, 4]
numbers.reverse()
print(numbers) # 输出 [4, 3, 2, 1]
[表达式 for 变量 in 可迭代对象 if 条件]
squares = [x**2 for x in range(1, 6)]
print(squares) # 输出 [1, 4, 9, 16, 25]
even_numbers = [x for x in range(10) if x % 2 == 0]
print(even_numbers) # 输出 [0, 2, 4, 6, 8]
matrix = [
[1, 2, 3],
[4, 5, 6],
[7, 8, 9]
]
print(matrix[1][2]) # 输出 6，访问第2行第3列

---

<!-- p.29 -->

8.6 列表的拷贝（了解）
列表的拷贝分为浅拷贝和深拷贝。
8.6.1 浅拷贝
浅拷贝只复制列表的第一层元素，嵌套的列表仍然是引用。
8.6.2 深拷贝
深拷贝递归地复制所有层级的元素，使用 copy 模块中的 deepcopy() 实现。
[1, [2, 3], 4]
deep_copy = copy.deepcopy(original)
deep_copy[1][0] = 99
print(original) # 输出 [1, [2, 3], 4]
元组转列表：使用 list() 将元组转换为列表。
集合转列表：使用 list() 将集合转换为列表。
9- 元祖
original = [1, [2, 3], 4]
shallow_copy = original.copy()
shallow_copy[1][0] = 99
print(original) # 输出 [1, [99, 3], 4]
import copy
original =
---
### 8.7 列表和其他数据类型的转换（了解）
Python 提供了多种内置函数，可以将其他数据类型转换为列表。
- **字符串转列表**：使用 `list()` 将字符串的每个字符转为列表元素。
```python
text = "hello"
text_list = list(text)
print(text_list) # 输出 ['h', 'e', 'l', 'l', 'o']
tuple_data = (1, 2, 3)
list_data = list(tuple_data)
print(list_data) # 输出 [1, 2, 3]
set_data = {1, 2, 3}
list_data = list(set_data)
print(list_data) # 输出 [1, 2, 3]

---

<!-- p.30 -->

9.1 元组的定义（掌握）
元组是一种有序的、不可变的数据结构，可以存储多个元素。与列表类似，元组可以包含任意数据类
型，但元组一旦创建，不能修改。元组使用小括号 () 表示，元素之间用逗号分隔。
定义元组：
9.2 元组的基本操作（掌握）
虽然元组是不可变的，但我们可以通过索引和切片访问其中的元素。
9.2.1 访问元组元素
使用索引访问元组中的单个元素，索引从 0 开始，支持负索引。
9.2.2 元组切片
使用切片获取元组中的一部分，格式为 元组[起始:结束:步长] 。
9.2.3 元组长度
使用 len() 函数获取元组的长度。
9.3 元组的常用方法（掌握）
元组提供的内置方法不多，主要用于基本操作，如统计元素出现次数和查找元素索引。
9.3.1 count() ：统计元素出现次数
使用 count(element) 方法统计指定元素在元组中出现的次数。
empty_tuple = () # 空元组
single_element_tuple = (42,) # 单个元素的元组，需在元素后加逗号
numbers = (1, 2, 3, 4, 5) # 包含多个元素的元组
mixed_tuple = (1, "hello", 3.14) # 包含不同数据类型的元组
numbers = (1, 2, 3, 4, 5)
print(numbers[0]) # 输出 1
print(numbers[-1]) # 输出 5（最后一个元素）
numbers = (1, 2, 3, 4, 5)
print(numbers[1:4]) # 输出 (2, 3, 4)
print(numbers[:3]) # 输出 (1, 2, 3)
print(numbers[::2]) # 输出 (1, 3, 5)
print(numbers[::-1]) # 输出 (5, 4, 3, 2, 1)（元组反转）
numbers = (1, 2, 3, 4, 5)
print(len(numbers)) # 输出 5
numbers = (1, 2, 2, 3, 4)
print(numbers.count(2)) # 输出 2

---

<!-- p.31 -->

9.3.2 index() ：查找元素的索引
使用 index(element) 方法返回指定元素在元组中的第一个匹配索引。如果元素不存在，会引发
ValueError 。
9.4 元组的不可变性（掌握）
元组的不可变性是其最重要的特性。元组一旦创建，元素就不能被修改、添加或删除。这一特性使元组
在需要不可变数据时特别有用，例如作为函数返回多个值或将元组作为字典的键。
示例：
9.5 元组解包（掌握）
元组解包是一种将元组中的元素直接赋值给多个变量的方式，非常方便。
示例：
应用场景：当一个函数返回多个值时，可以直接解包到多个变量中。
9.6 元组的嵌套（掌握）
元组可以包含其他元组，形成嵌套结构，适合表示多维数据或层级结构的数据。
示例：
numbers = (1, 2, 3, 4)
print(numbers.index(3)) # 输出 2
numbers = (1, 2, 3)
# numbers[0] = 10 # 会引发 TypeError，因为元组不可变
coordinates = (10, 20)
x, y = coordinates
print(x) # 输出 10
print(y) # 输出 20
def get_point():
return (5, 10)
x, y = get_point()
print(x, y) # 输出 5 10
nested_tuple = ((1, 2, 3), (4, 5, 6), (7, 8, 9))
print(nested_tuple[1][2]) # 输出 6，访问第2行第3列

---

<!-- p.32 -->

9.7 元组与列表的转换（掌握）
在 Python 中可以使用 tuple() 和 list() 进行元组与列表的相互转换，方便在需要可变或不可变数
据时灵活切换。
列表转换为元组：
元组转换为列表：
9.8 元组的使用场景（掌握）
由于元组不可变，且比列表更高效，因此在以下场景中更适合使用元组：
1. 多值返回：函数返回多个值时，可以将它们放在一个元组中。
2. 字典键：元组可以作为字典的键（因为元组是不可变类型），而列表不行。
3. 不需要修改的数据：当数据不需要修改时，用元组可以避免数据被意外改变，提高代码的安全性和
可读性。
示例：函数返回多个值：
9.9 元组的拷贝（了解）
元组的拷贝通常不需要特别处理，因为元组是不可变的，直接赋值就是拷贝。拷贝只是创建了新的引
用，指向相同的内存地址。
示例：
numbers_list = [1, 2, 3]
numbers_tuple = tuple(numbers_list)
print(numbers_tuple) # 输出 (1, 2, 3)
numbers_tuple = (1, 2, 3)
numbers_list = list(numbers_tuple)
print(numbers_list) # 输出 [1, 2, 3]
def get_person_info():
name = "aini"
age = 23
return name, age # 返回一个包含多个值的元组
info = get_person_info()
print(info) # 输出 ('aini', 23)
original_tuple = (1, 2, 3)
copy_tuple = original_tuple
print(copy_tuple is original_tuple) # 输出 True，两个变量指向相同对象

---

<!-- p.33 -->

9.10 元组的优点和局限性（了解）
9.10.1 优点
不可变性：确保数据的安全性，不会被意外修改。
高效：因为不可变，元组的性能比列表略高，尤其是在迭代和存储方面。
适合作为键：可以作为字典的键，而列表不能。
9.10.2 局限性
不可变：无法修改、添加或删除元素。
方法少：元组只提供了 count() 和 index() 两个方法，功能相对有限。
10- 字典
10.1 字典的定义（掌握）
字典是一种无序的键值对集合，用于存储和查找数据。字典通过键（key）来访问值（value），键必须
是唯一的且不可变的（通常为字符串或数字），而值可以是任意数据类型。字典使用大括号 {} 表示，
键值对之间用逗号分隔，键和值之间用冒号分隔。
定义字典：
10.2 字典的基本操作（掌握）
字典支持多种基本操作，如添加、修改、删除和访问键值对。
10.2.1 访问字典的值
使用键来访问字典中的值。如果键不存在会引发 KeyError ，可以使用 get() 方法避免异常。
10.2.2 添加和修改键值对
如果键已存在，则修改该键的值；如果键不存在，则添加新的键值对。
empty_dict = {} # 空字典
person = {"name": "aini", "age": 23, "city": "Shanghai"} # 包含多个键值对的字典
person = {"name": "aini", "age": 23}
print(person["name"]) # 输出 'aini'
print(person.get("age")) # 输出 23
print(person.get("gender", "N/A")) # 输出 'N/A'，若键不存在返回默认值
person = {"name": "aini", "age": 23}
person["city"] = "Shanghai" # 添加新的键值对
person["age"] = 24 # 修改已有键的值
print(person) # 输出 {'name': 'aini', 'age': 24, 'city':
'Shanghai'}

---

<!-- p.34 -->

10.2.3 删除键值对
使用 del 语句或 pop() 方法删除指定的键值对。 popitem() 方法可以随机删除字典中的最后一
对键值。
10.2.4 检查键是否存在
使用 in 关键字检查键是否存在于字典中。
10.3 字典的常用方法（掌握）
Python 提供了多种方法来操作字典，这些方法可以帮助我们进行遍历、更新和获取键值对等操作。
10.3.1 keys() ：获取所有键
使用 keys() 方法返回字典中所有键的视图。
10.3.2 values() ：获取所有值
使用 values() 方法返回字典中所有值的视图。
10.3.3 items() ：获取所有键值对
使用 items() 方法返回字典中所有键值对的视图，每个键值对以元组形式表示。
10.3.4 update() ：更新字典
使用 update() 方法将另一个字典或键值对序列合并到当前字典中，若有重复键则更新值。
person = {"name": "aini", "age": 23, "city": "Shanghai"}
del person["city"] # 删除指定键
age = person.pop("age") # 使用 pop() 获取并删除指定键
print(person) # 输出 {'name': 'aini'}
print(age) # 输出 23
person = {"name": "aini", "age": 23}
print("name" in person) # 输出 True
print("city" in person) # 输出 False
person = {"name": "aini", "age": 23}
print(person.keys()) # 输出 dict_keys(['name', 'age'])
person = {"name": "aini", "age": 23}
print(person.values()) # 输出 dict_values(['aini', 23])
person = {"name": "aini", "age": 23}
print(person.items()) # 输出 dict_items([('name', 'aini'),
('age', 23)])

---

<!-- p.35 -->

10.3.5 pop() 和 popitem() ：删除键值对
pop(key) ：删除并返回指定键的值。
popitem() ：随机删除并返回字典中的最后一个键值对（Python 3.7 以后为删除最后一对）。
10.3.6 clear() ：清空字典
使用 clear() 方法删除字典中的所有键值对，将字典清空。
10.4 字典的遍历（掌握）
字典遍历是字典操作中非常常见的一部分，通常用于处理每一个键值对。
遍历键：
遍历值：
遍历键值对：
person = {"name": "aini", "age": 23}
additional_info = {"city": "Shanghai", "age": 24}
person.update(additional_info)
print(person) # 输出 {'name': 'aini', 'age': 24, 'city':
'Shanghai'}
person = {"name": "aini", "age": 23, "city": "Shanghai"}
age = person.pop("age") # 删除并返回 'age' 的值
last_item = person.popitem() # 随机删除并返回最后一个键值对
print(age) # 输出 23
print(last_item) # 输出 ('city', 'Shanghai')
person = {"name": "aini", "age": 23}
person.clear()
print(person) # 输出 {}
person = {"name": "aini", "age": 23}
for key in person.keys():
print(key)
for value in person.values():
print(value)
for key, value in person.items():
print(f"{key}: {value}")

---

<!-- p.36 -->

10.5 字典的嵌套（掌握）
字典可以包含其他字典，形成嵌套结构，用于表示更复杂的数据关系。
示例：
10.6 字典生成式（掌握）
字典生成式（Dictionary Comprehension）是一种简洁的生成字典的方式，可以用一行代码创建一个新
的字典，常用于数据处理和过滤。
基本语法：
示例：
10.7 字典的拷贝（了解）
字典的拷贝分为浅拷贝和深拷贝。
10.7.1 浅拷贝
浅拷贝只复制字典的第一层元素，嵌套的字典仍然是引用。
10.7.2 深拷贝
深拷贝递归地复制所有层级的元素，使用 copy 模块中的 deepcopy() 实现。
student = {
"name": "aini",
"age": 23,
"courses": {
"math": 90,
"science": 85
}
}
print(student["courses"]["math"]) # 输出 90
{key_expr: value_expr for item in iterable if condition}
squares = {x: x**2 for x in range(1, 6)}
print(squares) # 输出 {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
original = {"name": "aini", "courses": {"math": 90}}
shallow_copy = original.copy()
shallow_copy["courses"]["math"] = 100
print(original) # 输出 {'name': 'aini', 'courses':
{'math': 100}}

---

<!-- p.37 -->

10.8 字典的使用场景（了解）
字典适合用于存储和查找数据的场景，尤其是在以下情况中：
1. 数据映射：存储键值对关系，如用户信息、配置数据等。
2. 计数：可以用字典来统计元素出现的频率。
3. 多层数据结构：当需要存储多层数据时，字典嵌套是常用方式。
示例：计数应用：
11- 集合
11.1 集合的定义（掌握）
集合是一个无序且不重复的元素集合。它通常用于去重、集合运算（交集、并集、差集等）等场景。集
合使用大括号 {} 表示，或者通过 set() 函数创建（适用于空集合）。
定义集合：
11.2 集合的基本操作（掌握）
集合支持添加、删除和检查元素是否存在等基本操作。
11.2.1 添加元素
使用 add() 方法将元素添加到集合中，如果元素已存在则不会重复添加。
import copy
original = {"name": "aini", "courses": {"math": 90}}
deep_copy = copy.deepcopy(original)
deep_copy["courses"]["math"] = 100
print(original) # 输出 {'name': 'aini', 'courses':
{'math': 90}}
words = ["apple", "banana", "apple", "cherry"]
word_count = {}
for word in words:
word_count[word] = word_count.get(word, 0) + 1
print(word_count) # 输出 {'apple': 2, 'banana': 1, 'cherry':
1}
empty_set = set() # 空集合，不能用 {} 创建空集合
fruits = {"apple", "banana", "cherry"} # 包含多个元素的集合
fruits = {"apple", "banana"}
fruits.add("cherry")
print(fruits) # 输出 {'apple', 'banana', 'cherry'}

---

<!-- p.38 -->

11.2.2 删除元素
使用 remove() 方法删除指定元素，如果元素不存在会引发 KeyError 。
使用 discard() 方法删除指定元素，如果元素不存在不会报错。
11.2.3 检查元素是否存在
使用 in 关键字检查元素是否存在于集合中。
11.3 集合的常用方法（掌握）
集合提供了丰富的方法来进行集合运算，如交集、并集、差集等。
11.3.1 union() 和 | ：并集
使用 union() 方法或 | 运算符获取两个集合的并集，返回一个新集合。
11.3.2 intersection() 和 & ：交集
使用 intersection() 方法或 & 运算符获取两个集合的交集，返回一个新集合。
11.3.3 difference() 和 - ：差集
使用 difference() 方法或 - 运算符获取集合的差集，返回一个新集合。
fruits = {"apple", "banana", "cherry"}
fruits.remove("banana")
fruits.discard("grape") # 不会报错
print(fruits) # 输出 {'apple', 'cherry'}
fruits = {"apple", "banana", "cherry"}
print("apple" in fruits) # 输出 True
print("grape" in fruits) # 输出 False
set1 = {1, 2, 3}
set2 = {3, 4, 5}
print(set1.union(set2)) # 输出 {1, 2, 3, 4, 5}
print(set1 | set2) # 输出 {1, 2, 3, 4, 5}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
print(set1.intersection(set2)) # 输出 {3}
print(set1 & set2) # 输出 {3}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
print(set1.difference(set2)) # 输出 {1, 2}
print(set1 - set2) # 输出 {1, 2}

---

<!-- p.39 -->

11.3.4 symmetric_difference() 和 ^ ：对称差集
使用 symmetric_difference() 方法或 ^ 运算符获取集合的对称差集，即在任一集合中但不在
两个集合中的元素。
11.4 集合的更新操作（掌握）
集合的更新操作会将另一个集合中的元素添加到当前集合中，通常会直接改变原集合。
11.4.1 update() 和 |= ：并集更新
使用 update() 方法或 |= 运算符将另一个集合的元素并入当前集合，直接修改原集合。
11.4.2 intersection_update() 和 &= ：交集更新
使用 intersection_update() 方法或 &= 运算符保留当前集合和另一个集合的交集，直接修改
原集合。
11.4.3 difference_update() 和 -= ：差集更新
使用 difference_update() 方法或 -= 运算符从当前集合中删除与另一个集合的交集元素，直接
修改原集合。
11.4.4 symmetric_difference_update() 和 ^= ：对称差集更新
使用 symmetric_difference_update() 方法或 ^= 运算符保留当前集合和另一个集合的对称差
集，直接修改原集合。
set1 = {1, 2, 3}
set2 = {3, 4, 5}
print(set1.symmetric_difference(set2)) # 输出 {1, 2, 4, 5}
print(set1 ^ set2) # 输出 {1, 2, 4, 5}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
set1.update(set2)
print(set1) # 输出 {1, 2, 3, 4, 5}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
set1.intersection_update(set2)
print(set1) # 输出 {3}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
set1.difference_update(set2)
print(set1) # 输出 {1, 2}
set1 = {1, 2, 3}
set2 = {3, 4, 5}
set1.symmetric_difference_update(set2)
print(set1) # 输出 {1, 2, 4, 5}

---

<!-- p.40 -->

11.5 集合的遍历（掌握）
可以使用 for 循环遍历集合中的每一个元素。
示例：
11.6 集合生成式（掌握）
集合生成式（Set Comprehension）是一种简洁的生成集合的方式，可以用一行代码创建一个新的集
合，常用于数据处理和过滤。
基本语法：
示例：
11.7 集合的使用场景（了解）
集合主要用于去重和集合运算的场景，在以下情况中非常有用：
1. 数据去重：可以快速删除重复元素。
2. 集合运算：交集、并集、差集和对称差集等集合操作。
3. 快速查找：集合中的查找操作的时间复杂度为 O(1) ，比列表更快。
示例：去重应用：
11.8 冻结集合（了解）
冻结集合（ frozenset ）是一种不可变集合，一旦创建就无法修改，类似于不可变的元组。冻结集合常
用于需要不可变集合的场景，例如字典的键。
创建冻结集合：
fruits = {"apple", "banana", "cherry"}
for fruit in fruits:
print(fruit)
{表达式 for 变量 in 可迭代对象 if 条件}
squares = {x**2 for x in range(1, 6)}
print(squares) # 输出 {1, 4, 9, 16, 25}
numbers = [1, 2, 2, 3, 4, 4, 5]
unique_numbers = set(numbers)
print(unique_numbers) # 输出 {1, 2, 3, 4, 5}
frozen_fruits = frozenset(["apple", "banana", "cherry"])
# frozen_fruits.add("grape") # 会引发 AttributeError，因为冻结集合不可修改
print(frozen_fruits) # 输出 frozenset({'apple', 'banana',
'cherry'})

---

<!-- p.41 -->

好的，下面将详细讲解 Python 中的 if 判断语句。 if 语句用于根据条件执行不同的代码块，是编写
控制流的重要工具。从基本语法、分支结构到嵌套和简写形式，将详细解释 if 判断的使用。知识点分
为“掌握”和“了解”两类，序号从 12.1 开始。
12- if判断
12.1 if 语句的基本语法（掌握）
if 语句用于根据条件执行代码块，如果条件为 True ，则执行 if 语句块中的代码；否则，跳过该代
码块。 if 语句的基本语法如下：
语法：
示例：
在上面的代码中，当 age >= 18 条件为 True 时，打印 "成年人"。
12.2 if-else 语句（掌握）
if-else 语句用于根据条件执行两个代码块之一。如果条件为 True ，执行 if 代码块；否则，执行
else 代码块。
语法：
示例：
在上面的代码中，当 age < 18 时， else 代码块中的内容会被执行。
if 条件:
代码块
age = 20
if age >= 18:
print("成年人") # 输出 "成年人"
if 条件:
代码块1
else:
代码块2
age = 16
if age >= 18:
print("成年人")
else:
print("未成年人") # 输出 "未成年人"

---

<!-- p.42 -->

12.3 if-elif-else 语句（掌握）
if-elif-else 语句用于处理多重条件判断。如果第一个条件为 False ，则检查下一个条件，以此类
推。可以包含多个 elif ，但 else 语句只能有一个，并且是可选的。
语法：
示例：
在上面的代码中，程序会从上到下依次判断条件，直到找到第一个满足条件的代码块。
12.4 嵌套的 if 语句（掌握）
if 语句可以嵌套在另一个 if 语句中，用于处理更复杂的逻辑。但嵌套层次不宜过深，以避免代码难
以阅读。
语法：
示例：
if 条件1:
代码块1
elif 条件2:
代码块2
elif 条件3:
代码块3
else:
代码块4
score = 85
if score >= 90:
print("优秀")
elif score >= 75:
print("良好") # 输出 "良好"
elif score >= 60:
print("及格")
else:
print("不及格")
if 条件1:
if 条件2:
代码块1
else:
代码块2
else:
代码块3

---

<!-- p.43 -->

在上面的代码中，当 age >= 18 且 has_id 为 True 时，执行 "允许进入"。
12.5 单行 if 表达式（掌握）
在一些简单的条件判断中，可以使用单行 if 表达式，将 if 和 else 的执行代码写在同一行。
语法：
示例：
在上面的代码中， if 表达式用于根据 age 的值返回不同的结果。
12.6 多条件判断（掌握）
在 if 语句中，可以使用逻辑运算符 and 和 or 实现多条件判断。
12.6.1 and 运算符
and 运算符：当所有条件为 True 时，返回 True ，否则返回 False 。
12.6.2 or 运算符
or 运算符：当至少一个条件为 True 时，返回 True ，否则返回 False 。
在多条件判断中，合理使用 and 和 or 可以更精确地控制代码逻辑。
age = 20
has_id = True
if age >= 18:
if has_id:
print("允许进入") # 输出 "允许进入"
else:
print("需要身份证")
else:
print("未成年人禁止进入")
代码块1 if 条件 else 代码块2
age = 20
result = "成年人" if age >= 18 else "未成年人"
print(result) # 输出 "成年人"
age = 20
has_id = True
if age >= 18 and has_id:
print("允许进入") # 输出 "允许进入"
age = 16
has_permission = True
if age >= 18 or has_permission:
print("允许进入") # 输出 "允许进入"

---

<!-- p.44 -->

12.7 if 判断的注意事项（了解）
在编写 if 判断时，有一些常见的注意事项，以避免代码错误或逻辑漏洞。
12.7.1 比较运算符的使用
确保使用正确的比较运算符（如 == 、 != 、 < 、 > 等）进行条件判断。错误的运算符可能导致逻
辑错误。
12.7.2 避免过深的嵌套
尽量避免过深的 if 嵌套，层级过多会影响代码的可读性和维护性。可以使用 elif 或提前返回等
方式优化嵌套结构。
12.7.3 注意缩进
Python 使用缩进来标识代码块，因此 if 判断中的代码块需要保持一致的缩进。缩进错误会导致
IndentationError 。
12.7.4 判断值的布尔性
在 if 判断中，可以直接使用变量名或表达式来检查其布尔性。例如， if my_list: 检查列表是
否为空。
12.8 综合示例（掌握）
通过一个综合示例来展示 if 判断在实际代码中的应用。
示例：根据用户输入的年龄，判断他们的分类：
在这个示例中，用户输入年龄，程序会根据不同的条件打印相应的分类。
13- for循环
my_list = [1, 2, 3]
if my_list:
print("列表不为空")
else:
print("列表为空")
age = int(input("请输入你的年龄: "))
if age < 12:
print("儿童")
elif 12 <= age < 18:
print("青少年")
elif 18 <= age < 65:
print("成年人")
else:
print("老年人")

---

<!-- p.45 -->

13.1 for 循环的基本语法（掌握）
for 循环用于从一个可迭代对象中逐一提取元素，并在循环体中对每个元素执行操作。基本语法如下：
语法：
示例：
在上面的示例中， for 循环依次提取 fruits 列表中的每一个元素，并打印出来。
13.2 使用 range() 函数进行数值循环（掌握）
range() 函数用于生成一系列数字，常用于指定循环的次数，生成的数字序列为左闭右开区间
[start, stop) 。
13.2.1 基本用法
语法：
示例：
13.3 遍历字符串（掌握）
字符串是一个字符序列，可以直接使用 for 循环逐个访问其中的字符。
示例：
for 变量 in 可迭代对象:
代码块
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
print(fruit)
range(stop)
range(start, stop)
range(start, stop, step)
# 从0到4的序列
for i in range(5):
print(i) # 输出 0, 1, 2, 3, 4
# 从2到6的序列
for i in range(2, 7):
print(i) # 输出 2, 3, 4, 5, 6
# 从1到9，每隔2步
for i in range(1, 10, 2):
print(i) # 输出 1, 3, 5, 7, 9

---

<!-- p.46 -->

在上面的代码中， for 循环逐个访问字符串 text 中的每一个字符并打印。
13.4 遍历列表和元组（掌握）
列表和元组都是可迭代对象，可以使用 for 循环逐个访问它们的元素。
示例：
元组遍历示例：
13.5 遍历字典（掌握）
字典是键值对的集合，可以使用 for 循环来遍历键、值或键值对。
13.5.1 遍历键
示例：
13.5.2 遍历值
示例：
13.5.3 遍历键值对
示例：
text = "Python"
for char in text:
print(char)
numbers = [1, 2, 3, 4, 5]
for num in numbers:
print(num)
items = (10, 20, 30)
for item in items:
print(item)
person = {"name": "aini", "age": 23}
for key in person:
print(key) # 输出 "name" 和 "age"
for value in person.values():
print(value) # 输出 "aini" 和 23
for key, value in person.items():
print(f"{key}: {value}") # 输出 "name: aini" 和 "age: 23"

---

<!-- p.47 -->

13.6 嵌套的 for 循环（掌握）
在 for 循环内部可以嵌套另一个 for 循环，通常用于处理二维数据结构（如列表嵌套列表）。
示例：
在上面的代码中，外层循环遍历每一行，内层循环遍历每行中的每一个元素。
13.7 使用 enumerate() 函数获取索引和元素（掌握）
enumerate() 函数用于在 for 循环中同时获取元素的索引和元素本身，适合在遍历时需要索引的场
景。
示例：
输出：
13.8 使用 zip() 函数并行遍历多个列表（掌握）
zip() 函数用于将多个可迭代对象组合成一个迭代器，以便在 for 循环中并行遍历多个序列。
示例：
输出：
matrix = [
[1, 2, 3],
[4, 5, 6],
[7, 8, 9]
]
for row in matrix:
for element in row:
print(element, end=" ") # 输出 1 2 3 4 5 6 7 8 9
print() # 换行
fruits = ["apple", "banana", "cherry"]
for index, fruit in enumerate(fruits):
print(f"{index}: {fruit}")
0: apple
1: banana
2: cherry
names = ["aini", "zhang", "li"]
ages = [23, 25, 30]
for name, age in zip(names, ages):
print(f"{name} is {age} years old.")
aini is 23 years old.
zhang is 25 years old.
li is 30 years old.

---

<!-- p.48 -->

13.9 列表生成式中的 for 循环（掌握）
列表生成式（List Comprehension）是一种简洁的生成列表的方法，通常用来将 for 循环和条件判断
结合起来生成新的列表。
基本语法：
示例：
13.10 for-else 语句（了解）
for-else 语句中的 else 块会在 for 循环正常完成后执行，如果循环被 break 语句提前终止，则不
执行 else 块。该语句结构相对少用。
示例：
在上面的代码中， for 循环因 break 终止， else 块不会执行。
13.11 for 循环的注意事项（了解）
在编写 for 循环时，有一些常见的注意事项，以避免逻辑错误或效率低下：
1. 避免修改可迭代对象：在 for 循环中修改正在迭代的对象（如添加或删除元素）可能导致循环行
为异常。
2. 合理使用 range() 和 enumerate() ：当需要索引时使用 enumerate() ，避免手动维护索引。
3. 避免嵌套过深：多层嵌套会导致代码复杂且难以维护，尽量优化循环结构。
14- while循环
14.1 while 循环的基本语法（掌握）
while 循环在指定条件为 True 时不断重复执行代码块，直到条件为 False 时结束循环。 while 循
环的语法结构如下：
语法：
[表达式 for 变量 in 可迭代对象 if 条件]
squares = [x**2 for x in range(1, 6)]
print(squares) # 输出 [1, 4, 9, 16, 25]
numbers = [1, 2, 3, 4, 5]
for num in numbers:
if num == 3:
print("Found 3!")
break
else:
print("3 not found.")

---

<!-- p.49 -->

示例：
输出：
在上面的代码中， while 循环会在 count <= 5 为 True 时执行，直到 count 增加到 6，条件
变为 False 时终止循环。
14.2 无限循环（掌握）
如果 while 循环的条件一直为 True ，则会形成无限循环。在某些情况下，程序需要一直运行直到满足
特定的退出条件。
示例：
在上面的代码中，程序会一直运行，直到用户输入 "exit" 时，通过 break 退出循环。
14.3 使用 break 和 continue 控制循环（掌握）
break 和 continue 是控制循环的两个关键字，可以用来在特定条件下中断或跳过循环的执行。
14.3.1 break ：中断循环
break 用于立即退出循环，不再执行循环体的剩余部分。
输出：
while 条件:
代码块
count = 1
while count <= 5:
print(count)
count += 1
1
2
3
4
5
while True:
user_input = input("请输入 'exit' 退出: ")
if user_input == "exit":
break
count = 1
while count <= 5:
if count == 3:
break
print(count)
count += 1

---

<!-- p.50 -->

在上面的代码中，当 count 为 3 时， break 语句会中断循环。
14.3.2 continue ：跳过本次循环
continue 用于跳过当前循环的剩余部分，立即开始下一次循环。
输出：
在上面的代码中，当 count 为 3 时， continue 会跳过本次循环的剩余部分。
14.4 while-else 语句（了解）
while-else 语句中的 else 块会在 while 循环正常完成后执行，如果循环被 break 语句提前终止，
则不会执行 else 块。
示例：
输出：
在上面的代码中，当 while 循环正常结束时， else 块会被执行。
1
2
count = 0
while count < 5:
count += 1
if count == 3:
continue
print(count)
1
2
4
5
count = 1
while count <= 3:
print(count)
count += 1
else:
print("循环结束")
1
2
3
循环结束

---

<!-- p.51 -->

14.5 使用 while 循环处理用户输入（掌握）
while 循环常用于处理用户输入，直到用户输入有效的内容为止。
示例：
在上面的代码中， while 循环不断询问用户输入数字，直到用户输入 "exit" 时退出程序。
14.6 while 循环中的计数器（掌握）
使用 while 循环时，经常需要设置计数器来控制循环次数，计数器通常会在每次循环结束后递增或递
减。
示例：
输出：
在上面的代码中， count 是计数器，控制 while 循环的次数。
14.7 嵌套的 while 循环（了解）
while 循环可以嵌套在另一个 while 循环中，用于处理多层循环结构。
示例：
while True:
user_input = input("请输入一个数字 (输入 'exit' 退出): ")
if user_input == "exit":
print("退出程序")
break
elif user_input.isdigit():
print(f"您输入的数字是 {user_input}")
else:
print("无效输入，请输入数字")
count = 0
while count < 5:
print("当前计数:", count)
count += 1
当前计数: 0
当前计数: 1
当前计数: 2
当前计数: 3
当前计数: 4

---

<!-- p.52 -->

输出：
在上面的代码中，外层 while 控制 outer 计数，内层 while 控制 inner 计数。
14.8 while 循环的注意事项（了解）
在编写 while 循环时，有一些常见的注意事项，以避免代码运行出错或陷入死循环。
1. 避免死循环：确保循环条件最终会变为 False ，否则可能导致死循环，程序无法退出。
2. 计数器控制：使用计数器时，记得在每次循环中更新计数器的值，否则可能造成无限循环。
3. 合理使用 break 和 continue ： break 和 continue 能提高循环的灵活性，但要避免滥用，以
免影响代码的可读性。
15- for循环和while循环比较
15.1 基本区别（掌握）
for 循环：用于遍历可迭代对象（如列表、元组、字符串、字典、集合等）中的每一个元素，通
常适用于明确知道迭代次数的场景。
while 循环：在条件为 True 时不断执行代码块，适用于不确定迭代次数的场景，直到某一条件
满足才结束循环。
15.2 语法结构对比（掌握）
for 循环的基本语法
outer = 1
while outer <= 3:
inner = 1
while inner <= 2:
print(f"外层: {outer}, 内层: {inner}")
inner += 1
outer += 1
外层: 1, 内层: 1
外层: 1, 内层: 2
外层: 2, 内层: 1
外层: 2, 内层: 2
外层: 3, 内层: 1
外层: 3, 内层: 2
for 变量 in 可迭代对象:
代码块

---

<!-- p.53 -->

特性 for 循环 while 循环
适用情况 明确的迭代次数或固定的序列 不确定的迭代次数，基于条件的循环
可读性 代码简洁明了，适合处理序列 适合动态条件的循环，但逻辑略复杂
灵活性 依赖可迭代对象或 range 控制次数 可处理任意复杂的条件
效率 更适合于遍历对象，代码效率高 适合条件控制，可能会陷入死循环
while 循环的基本语法
15.3 使用场景（掌握）
for 循环的适用场景
遍历已知长度的可迭代对象：如列表、字符串、元组等，直接遍历元素。
需要计数的循环：可以与 range() 配合，执行固定次数的循环。
生成列表：列表生成式通常使用 for 循环生成。
while 循环的适用场景
条件控制的循环：在满足条件时重复执行代码，而不是固定次数。
用户输入验证：不断检查输入，直到符合要求为止。
无限循环：在服务器或实时监控中常见，通过 while True 持续执行，直到满足某个终止条件。
15.4 优缺点比较（掌握）
15.5 for 和 while 循环的替换（掌握）
在某些情况下， for 和 while 循环可以相互替换：
15.5.1 使用 while 循环模拟 for 循环
示例：用 while 模拟一个固定次数的循环。
等价于：
while 条件:
代码块
i = 0
while i < 5:
print(i)
i += 1
for i in range(5):
print(i)

---

<!-- p.54 -->

15.5.2 使用 for 循环模拟简单的条件控制
虽然 for 循环并不直接适用于条件控制，但可以通过遍历 itertools.cycle 实现无限循环，并在循
环体中条件判断以 break 退出。
15.6 示例对比（掌握）
示例 1：遍历列表
for 循环：
while 循环：
示例 2：条件控制的循环
for 循环（通过 break 终止）：
while 循环：
from itertools import cycle
for _ in cycle([None]):
user_input = input("请输入 'exit' 退出: ")
if user_input == "exit":
break
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
print(fruit)
fruits = ["apple", "banana", "cherry"]
i = 0
while i < len(fruits):
print(fruits[i])
i += 1
for _ in range(100): # 实际上是人为限定了次数
user_input = input("请输入 'exit' 退出: ")
if user_input == "exit":
break
while True:
user_input = input("请输入 'exit' 退出: ")
if user_input == "exit":
break

---

<!-- p.55 -->

15.7 循环的嵌套使用（了解）
for 和 while 循环可以嵌套使用，适合处理多层数据结构或条件复杂的情况。
示例：遍历二维列表中的元素，并根据条件判断是否打印
在这个示例中， for 循环用于遍历列表，而条件判断和打印操作可以在嵌套循环中控制。
15.8 优先选择哪种循环（掌握）
选择 for 循环：当明确知道迭代次数或需要遍历可迭代对象时，优先选择 for 循环。它的结构清
晰、代码简洁。
选择 while 循环：当循环次数不确定或需要条件控制时，选择 while 循环。它在处理需要灵活
控制结束条件的场景中更合适。
16- 循环综合练习题
1. 输出 1 到 10 的所有数字
思路：使用 for 循环遍历从 1 到 10 的范围，逐个输出数字。
2. 计算 1 到 100 的和
思路：使用 for 循环遍历 1 到 100，将每个数累加到一个变量中。
matrix = [
[1, 2, 3],
[4, 5, 6],
[7, 8, 9]
]
for row in matrix:
for element in row:
if element % 2 == 0:
print(element)
for i in range(1, 11):
print(i) # 输出 1 到 10 的数字
total = 0
for i in range(1, 101):
total += i # 每次循环累加当前数到总和中
print("1到100的和为:", total)

---

<!-- p.56 -->

3. 输出列表中的所有元素
思路：使用 for 循环遍历列表，并打印每个元素。
4. 打印 1 到 50 中所有的偶数
思路：使用 for 循环遍历 1 到 50，检查每个数是否为偶数，是偶数则输出。
5. 计算一个列表中所有数字的和
思路：遍历列表中的每个数字，并累加到一个变量中。
6. 找到列表中最大值
思路：初始化最大值为第一个元素，然后遍历列表，逐个比较并更新最大值。
7. 打印九九乘法表
思路：使用嵌套的 for 循环，外层循环控制乘数 1 到 9，内层循环控制被乘数 1 到 9。
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
print(fruit) # 输出每个水果的名字
for i in range(1, 51):
if i % 2 == 0: # 如果数是偶数
print(i) # 输出偶数
numbers = [10, 20, 30, 40]
total = 0
for num in numbers:
total += num # 累加每个数到总和
print("列表中所有数字的和为:", total)
numbers = [3, 5, 7, 2, 8]
max_num = numbers[0] # 假设第一个数为最大值
for num in numbers:
if num > max_num:
max_num = num # 更新最大值
print("列表中的最大值是:", max_num)
for i in range(1, 10):
for j in range(1, i + 1):
print(f"{j} * {i} = {i * j}", end=" ") # 打印乘法表
print() # 换行

---

<!-- p.57 -->

8. 反转一个字符串
思路：使用 for 循环从字符串末尾开始逐个字符提取，并累加到新字符串中。
9. 统计列表中正数的个数
思路：遍历列表，检查每个数字是否为正数，是则计数加一。
10. 找到两个列表的交集
思路：使用 for 循环遍历第一个列表，检查是否在第二个列表中。
11. 输出一个列表中所有非零元素
思路：遍历列表，检查每个元素是否不为零，不为零则输出。
12. 打印一个字符串中所有的字母
思路：遍历字符串，检查每个字符是否为字母，如果是则打印。
text = "hello"
reversed_text = ""
for char in text[::-1]: # 从末尾到开头遍历字符
reversed_text += char
print("反转后的字符串为:", reversed_text)
numbers = [-5, 3, 8, -2, 6]
count = 0
for num in numbers:
if num > 0:
count += 1 # 计数加一
print("列表中正数的个数为:", count)
list1 = [1, 2, 3, 4]
list2 = [3, 4, 5, 6]
intersection = []
for item in list1:
if item in list2:
intersection.append(item)
print("两个列表的交集为:", intersection)
numbers = [0, 5, 3, 0, 8]
for num in numbers:
if num != 0:
print(num) # 输出非零元素

---

<!-- p.58 -->

13. 计算一个数的阶乘
思路：使用 for 循环从 1 到 n ，逐个相乘计算阶乘。
14. 打印一个列表中的奇数位置元素
思路：使用 for 循环结合 range() ，遍历奇数位置索引的元素。
15. 求出 1 到 50 的所有数的平方和
思路：使用 for 循环遍历 1 到 50，将每个数的平方累加到总和中。
16. 输出一个字符串中所有的数字
思路：使用 for 循环遍历字符串，检查每个字符是否为数字，是则输出。
17. 打印出所有质数（2 到 50）
思路：使用嵌套循环，外层遍历 2 到 50，内层检查每个数是否有除 1 和自身之外的因数。
text = "Hello123"
for char in text:
if char.isalpha(): # 检查是否是字母
print(char)
n = 5
factorial = 1
for i in range(1, n + 1):
factorial *= i
print(f"{n} 的阶乘是:", factorial)
numbers = [10, 20, 30, 40, 50]
for i in range(1, len(numbers), 2):
print(numbers[i]) # 输出奇数位置的元素
total = 0
for i in range(1, 51):
total += i ** 2 # 累加平方
print("1到50的平方和为:", total)
text = "abc123def456"
for char in text:
if char.isdigit(): # 检查是否是数字
print(char)

---

<!-- p.59 -->

18. 找到列表中最小值
思路：假设第一个元素为最小值，遍历比较更新。
19. 判断一个字符串是否是回文
思路：检查字符串是否与反转后的字符串相同。
20. 计算一个字符串中每个字符的出现次数
思路：使用字典存储字符和对应出现次数。
17- 循环判断练习题（较难）
10.1 判断素数
题目描述
编写一个程序，判断用户输入的一个正整数是否为素数。
for num in range(2, 51):
is_prime = True
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
is_prime = False
break
if is_prime:
print(num)
numbers = [4, 2, 9, 1, 5]
min_num = numbers[0]
for num in numbers:
if num < min_num:
min_num = num
print("列表中的最小值为:", min_num)
text = "level"
is_palindrome = text == text[::-1]
print(f"{text} 是回文" if is_palindrome else f"{text} 不是回文")
text = "hello world"
count_dict = {}
for char in text:
count_dict[char] = count_dict.get(char, 0) + 1
print("每个字符的出现次数为:", count_dict)

---

<!-- p.60 -->

解题思路
输入一个正整数。
使用循环判断从2到该数的平方根是否有整除的数。
代码详解
10.2 打印斐波那契数列
题目描述
编写一个程序，输出斐波那契数列的前n项，n由用户输入。
解题思路
使用循环生成斐波那契数列。
代码详解
10.3 冒泡排序
题目描述
实现一个冒泡排序算法，要求用户输入一组整数，然后输出排序后的结果。
解题思路
使用嵌套循环比较相邻元素。
num = int(input("请输入一个正整数: "))
is_prime = True
if num < 2:
is_prime = False
else:
for i in range(2, int(num**0.5) + 1):
if num % i == 0:
is_prime = False
break
if is_prime:
print(f"{num} 是素数")
else:
print(f"{num} 不是素数")
n = int(input("请输入要输出的斐波那契数列项数: "))
a, b = 0, 1
fib_seq = []
for _ in range(n):
fib_seq.append(a)
a, b = b, a + b
print(fib_seq)

---

<!-- p.61 -->

代码详解
10.4 统计字符频率
题目描述
编写程序，统计输入字符串中每个字符出现的频率，并输出结果。
解题思路
使用字典存储字符和其频率。
代码详解
10.5 查找最大子序列和
题目描述
给定一个整数数组，编写程序找出具有最大和的连续子序列。
解题思路
使用动态规划维护当前的子序列和和最大子序列和。
代码详解
arr = list(map(int, input("请输入一组整数，用空格分隔: ").split()))
n = len(arr)
for i in range(n):
for j in range(0, n - i - 1):
if arr[j] > arr[j + 1]:
arr[j], arr[j + 1] = arr[j + 1], arr[j]
print("排序后的数组:", arr)
input_string = input("请输入字符串: ")
freq = {}
for char in input_string:
freq[char] = freq.get(char, 0) + 1
print("字符频率:", freq)
array = list(map(int, input("请输入整数数组，用空格分隔: ").split()))
max_sum = float('-inf')
current_sum = 0
for num in array:
current_sum += num
if current_sum > max_sum:
max_sum = current_sum
if current_sum < 0:
current_sum = 0
print("最大子序列和:", max_sum)

---

<!-- p.62 -->

10.6 查找重复元素
题目描述
编写程序，找出输入列表中所有重复的元素。
解题思路
使用集合存储已见过的元素。
代码详解
10.7 计算阶乘
题目描述
编写程序，计算一个正整数的阶乘。
解题思路
使用循环从1乘到n。
代码详解
10.8 查找数组中第K大的元素
题目描述
编写程序，找出数组中第K大的元素。
解题思路
使用排序的方法，先对数组进行排序。
代码详解
input_list = list(map(int, input("请输入整数列表，用空格分隔: ").split()))
seen = set()
duplicates = set()
for num in input_list:
if num in seen:
duplicates.add(num)
else:
seen.add(num)
print("重复的元素:", duplicates)
num = int(input("请输入一个正整数: "))
result = 1
for i in range(1, num + 1):
result *= i
print("阶乘是:", result)

---

<!-- p.63 -->

10.9 验证回文数
题目描述
编写程序，判断一个字符串是否为回文。
解题思路
比较字符串的前后字符。
代码详解
10.10 爬楼梯问题
题目描述
假设每次可以爬1阶或2阶，编写程序计算爬到n阶的不同方式数。
解题思路
使用动态规划的思想。
代码详解
array = list(map(int, input("请输入整数数组，用空格分隔: ").split()))
k = int(input("请输入K值: "))
unique_elements = list(set(array))
unique_elements.sort(reverse=True)
print(f"数组中第{k}大的元素是: {unique_elements[k - 1]}")
input_string = input("请输入字符串: ")
is_palindrome = True
length = len(input_string)
for i in range(length // 2):
if input_string[i] != input_string[length - 1 - i]:
is_palindrome = False
break
if is_palindrome:
print(f"{input_string} 是回文")
else:
print(f"{input_string} 不是回文")
n = int(input("请输入楼梯的阶数: "))
if n == 1:
print("不同的爬楼梯方式数: 1")
elif n == 2:
print("不同的爬楼梯方式数: 2")
else:
dp = [0] * (n + 1)
dp[1], dp[2] = 1, 2
for i in range(3, n + 1):
dp[i] = dp[i - 1] + dp[i - 2]
print("不同的爬楼梯方式数:", dp[n])

---

<!-- p.64 -->

18- 函数
18.1 函数的定义（掌握）
函数是一个可重用的代码块，用于执行特定的任务。函数可以接收输入参数并返回结果，帮助我们组织
代码并提高可读性和可维护性。
定义函数的基本语法：
示例：
18.2 函数的调用（掌握）
函数定义后可以通过调用来执行。函数调用可以传递参数，调用函数时参数的顺序要与定义时一致。
示例：
18.3 函数的参数（掌握）
函数可以接收参数，参数是函数外部传入的值，函数内部可以使用这些值。
18.3.1 位置参数
定义和调用：
def function_name(parameters):
"""可选的文档字符串"""
# 函数体
return result # 可选的返回值
def greet(name):
"""打印问候信息"""
print(f"Hello, {name}!")
greet("Alice") # 调用函数，输出: Hello, Alice!
def add(a, b):
"""返回两个数的和"""
return a + b
result = add(5, 3) # 调用函数，传递参数
print(result) # 输出: 8
def multiply(x, y):
return x * y
print(multiply(2, 3)) # 输出: 6

---

<!-- p.65 -->

18.3.2 默认参数
定义默认参数：在定义函数时，可以为参数指定默认值，调用时可以选择性传入参数。
18.3.3 可变参数
使用 *args 和 **kwargs ： *args 用于传入任意数量的位置参数， **kwargs 用于传入任意数
量的关键字参数。
18.4 函数的返回值（掌握）
函数可以返回结果，使用 return 语句指定返回值。如果没有 return ，函数将返回 None 。
示例：
18.4.1 多个返回值
返回多个值：可以使用逗号分隔多个值。
def power(base, exponent=2):
return base ** exponent
print(power(3)) # 输出: 9 (使用默认 exponent)
print(power(3, 3)) # 输出: 27 (覆盖默认 exponent)
def sum_all(*args):
return sum(args)
print(sum_all(1, 2, 3, 4)) # 输出: 10
def print_info(**kwargs):
for key, value in kwargs.items():
print(f"{key}: {value}")
print_info(name="Alice", age=30) # 输出: name: Alice, age: 30
def square(n):
return n * n
result = square(4)
print(result) # 输出: 16
def divide(a, b):
return a // b, a % b # 返回商和余数
quotient, remainder = divide(10, 3)
print(quotient, remainder) # 输出: 3 1

---

<!-- p.66 -->

18.5 函数的文档字符串（掌握）
文档字符串（docstring）是函数定义中的字符串，用于描述函数的功能。文档字符串通常是函数的第一
行，可以通过 help() 函数查看。
示例：
18.6 函数的作用域（掌握）
变量的作用域决定了其可见性和生命周期。在 Python 中，变量有局部作用域和全局作用域。
18.6.1 局部变量
在函数内定义的变量：只在函数内有效，外部无法访问。
18.6.2 全局变量
在函数外定义的变量：可以在整个程序中访问。
18.6.3 使用 global 关键字
在函数内部修改全局变量：可以使用 global 关键字声明。
def subtract(a, b):
"""返回 a 和 b 的差值"""
return a - b
print(help(subtract)) # 查看文档字符串
def func():
local_var = 10 # 局部变量
print(local_var)
func()
# print(local_var) # 会引发 NameError
global_var = 20 # 全局变量
def func():
print(global_var) # 可以访问全局变量
func() # 输出: 20
global_var = 30
def modify_global():
global global_var # 声明使用全局变量
global_var += 10
modify_global()
print(global_var) # 输出: 40

---

<!-- p.67 -->

18.7 高阶函数（掌握）
高阶函数是指接受函数作为参数或返回一个函数的函数。在 Python 中，函数是第一类对象，可以作为
参数传递。
18.7.1 函数作为参数
示例：
18.7.2 返回函数
示例：
18.8 匿名函数（了解）
匿名函数（lambda 函数）是一种没有名字的函数，通常用于需要小型函数的场景，如在 map() 、
filter() 和 sorted() 等函数中使用。
示例：
def apply_function(func, value):
return func(value)
def square(n):
return n * n
result = apply_function(square, 5)
print(result) # 输出: 25
def outer_function(msg):
def inner_function():
print(msg)
return inner_function # 返回内嵌函数
my_func = outer_function("Hello, World!")
my_func() # 输出: Hello, World!
square = lambda x: x * x
print(square(5)) # 输出: 25
# 使用 map() 函数
numbers = [1, 2, 3, 4]
squares = list(map(lambda x: x ** 2, numbers))
print(squares) # 输出: [1, 4, 9, 16]
语法：使用关键字def
例如:
def f():
......
默认参数格式：
例如:
def power(x, n=2): # n：默认参数，缺省参数
return x**n

---

<!-- p.68 -->

19- 全局变量和局部变量
注意:如果中间参数想使用默认参数，下一个之后的参数应该标注对应的变量名
def infos(name,age=24,gender='女'):
return '大家好，我叫%s ，我今年%d岁，我是一名%s生'%(name,age,gender)
s = infos('mia',24,'女')
lily = infos('lily')
jack = infos('jack',gender='男')
print(jack)
print(lily)
可变参数:
例如:
def total(*args): # 可变参数
print(args)
result = 0
for i in args:
result += i*i
return result
result = total(1,4,5,6,7,8,3)
print(result)
result = total(3,4,5)
a = [1,2,3,4,5]
result = total(*a)
print(result)
def f(**kwargs): # 可变参数，接收字典
for k,v in kwargs.items():
print(k,v)
d = {'name':'xiaoming','age':18}
f(**d)
变量作用域:
使用关键字global表明对全局变量进行修改
匿名函数:
例如:
fun = lambda a,b:a+b
result = fun(5,2)
a = [1,2,3,4,5]
result = map(lambda x:x**3, a) # 映射
print(list(result))
# reduce 累积
from functools import reduce
result = reduce(lambda x,y:x*y,a)
print(result)
# filter 过滤
result = filter(lambda x:x%2,a)
print(list(result))

---

<!-- p.69 -->

19.1 变量的作用域（掌握）
在编程中，作用域指的是变量可以被访问的范围。在 Python 中，变量的作用域分为局部作用域和全局
作用域。
局部作用域（Local Scope）：在函数内部定义的变量，只能在该函数内部使用，函数外部无法访
问这些变量。
全局作用域（Global Scope）：在整个程序中定义的变量，通常位于函数外部，可以在程序的任
何位置访问。
19.2 局部变量（掌握）
局部变量是在函数内部定义的变量。它的作用范围仅限于该函数，函数外部无法访问这个变量。局部变
量的生命周期在函数执行期间，当函数执行完毕，局部变量也随之销毁。
19.2.1 局部变量的定义和访问
定义：在函数内部直接赋值给变量即定义了局部变量。
访问：只能在定义它的函数内部访问。
示例：
在上面的示例中， local_var 是 my_function() 函数内部的局部变量，它只能在该函数内部使用。
函数外部无法访问 local_var ，否则会引发 NameError 。
19.2.2 局部变量的优先级
在函数内部，如果局部变量和全局变量同名，局部变量会优先被使用。局部变量的优先级高于同名的全
局变量。
示例：
在这个示例中，虽然 x 在函数外部被定义为全局变量，但在 my_function() 中重新定义了一个同名的
局部变量 x ，因此在函数内部会使用局部变量，而不会影响函数外部的全局变量。
def my_function():
local_var = 10 # 局部变量
print("局部变量:", local_var)
my_function() # 输出: 局部变量: 10
# print(local_var) # 会引发 NameError，因为函数外无法访问 local_var
x = 5 # 全局变量
def my_function():
x = 10 # 局部变量
print("函数内部的 x:", x) # 输出: 函数内部的 x: 10
my_function()
print("函数外部的 x:", x) # 输出: 函数外部的 x: 5

---

<!-- p.70 -->

19.3 全局变量（掌握）
全局变量是在函数外部定义的变量。全局变量可以在整个程序的任何地方访问，包括函数内部和外部。
全局变量的生命周期贯穿程序的执行过程。
19.3.1 全局变量的定义和访问
定义：在函数外部直接赋值给变量。
访问：可以在函数内部和外部访问。
示例：
在这个示例中， global_var 是一个全局变量，既可以在 my_function() 函数内访问，也可以在函数
外部访问。
19.3.2 使用 global 关键字修改全局变量
在函数内部，可以通过 global 关键字声明一个变量为全局变量，从而修改该全局变量的值。
示例：
在这个示例中，通过 global count 声明 count 为全局变量，从而可以在 increment() 函数中修改
count 的值。
19.3.3 不使用 global 的情况下
如果没有使用 global 关键字直接在函数内部赋值同名变量，Python 会将该变量视为局部变量，不会
影响同名的全局变量。
示例：
global_var = 20 # 全局变量
def my_function():
print("函数内部的全局变量:", global_var)
my_function() # 输出: 函数内部的全局变量: 20
print("函数外部的全局变量:", global_var) # 输出: 函数外部的全局变量: 20
count = 0 # 全局变量
def increment():
global count # 声明使用全局变量
count += 1 # 修改全局变量
increment()
print("全局变量 count 的值:", count) # 输出: 全局变量 count 的值: 1
total = 100 # 全局变量
def reset_total():
total = 0 # 局部变量，不会影响全局的 total
print("函数内部的 total:", total) # 输出: 函数内部的 total: 0
reset_total()
print("全局的 total:", total) # 输出: 全局的 total: 100

---

<!-- p.71 -->

在这个示例中，函数 reset_total() 中定义的 total 是一个局部变量，并不会影响函数外部的全局
变量 total 。
19.4 全局变量和局部变量的注意事项（掌握）
1. 避免过度使用全局变量：全局变量在程序的任何地方都可以被修改，可能会导致意外错误。通常建
议使用局部变量，除非确有必要才使用全局变量。
2. global 的使用：如果需要在函数内部修改全局变量，必须使用 global 关键字，否则 Python 会
默认将其视为局部变量。
3. 变量的生命周期：全局变量在程序运行期间始终存在，而局部变量只在函数执行期间有效，函数执
行结束后局部变量会被销毁。
4. 命名冲突：避免在局部作用域中定义与全局变量同名的变量，以免造成混淆。
5. 可读性问题：过多的全局变量会降低代码的可读性和可维护性，增加调试难度。
19.5 全局变量和局部变量的综合示例（掌握）
以下是一个综合示例，展示全局变量、局部变量和 global 关键字的使用场景。
示例：
在这个示例中， balance 是一个全局变量，用于记录账户余额。 deposit() 、 withdraw() 和
check_balance() 是三个函数，分别用于存款、取款和查询余额。 deposit() 和 withdraw() 函数
通过 global 关键字来声明 balance 为全局变量，从而可以在函数内部修改全局变量 balance 的
值。
20- 综合案例
balance = 1000 # 全局变量，初始余额
def deposit(amount):
"""存款操作"""
global balance # 声明 balance 为全局变量
balance += amount # 修改全局变量
print(f"存款 {amount} 元，当前余额：{balance}")
def withdraw(amount):
"""取款操作"""
if amount > balance:
print("余额不足")
else:
global balance
balance -= amount
print(f"取款 {amount} 元，当前余额：{balance}")
def check_balance():
"""查询余额"""
print(f"当前余额为：{balance}")
# 操作示例
deposit(500) # 存款 500 元
withdraw(200) # 取款 200 元
check_balance() # 查询余额

---

<!-- p.72 -->

1. 寻找满足条件的数字“自反数”
题目：定义自反数：一个整数 n 满足以下条件时称为自反数：
1. n 是一个四位数。
2. n 可以被 4 整除。
3. n 的数位的平方和等于 n 自身。
请编写一个函数 is_autoreflective(num) 来判断一个数是否为自反数，并找出 1000 到 9999 之间的
所有自反数。
思路分析：
1. 使用嵌套循环提取各位数字。
2. 检查是否为四位数、可被 4 整除、并且数位平方和等于数本身。
3. 使用 is_autoreflective 函数检查数字条件，在主程序中遍历范围并输出。
代码详解：
2. 判断“亲密素数对”
题目：定义亲密素数对：如果两个素数之差等于 2，则称它们为亲密素数对。例如 (3, 5) 和 (11, 13) 是亲
密素数对。编写函数 is_prime(num) 判断一个数是否为素数，找到 1 到 100 之间的所有亲密素数对。
思路分析：
1. 编写 is_prime(num) 函数判断一个数是否为素数。
2. 遍历 1 到 100 的素数，检查每对素数之间的差是否等于 2。
3. 如果差值满足条件，则将素数对存储在列表中并输出。
代码详解：
def is_autoreflective(num):
"""判断一个数是否为自反数"""
if num % 4 != 0:
return False
thousands = num // 1000
hundreds = (num // 100) % 10
tens = (num // 10) % 10
units = num % 10
return (thousands**2 + hundreds**2 + tens**2 + units**2) == num
# 找出所有自反数
autoreflective_numbers = []
for i in range(1000, 10000):
if is_autoreflective(i):
autoreflective_numbers.append(i)
print("所有自反数为：", autoreflective_numbers)
def is_prime(num):
"""判断一个数是否为素数"""
if num < 2:
return False
for i in range(2, int(num ** 0.5) + 1):

---

<!-- p.73 -->

3. 生成和验证“循环素数”
题目：循环素数是指通过循环排列数位生成的新数字也都是素数。例如，197 是循环素数，因为 197、
971 和 719 都是素数。编写函数 is_circular_prime(num) 判断一个数是否为循环素数，找出 1 到
100 之间的所有循环素数。
思路分析：
1. 编写 is_prime(num) 判断素数。
2. 编写 generate_rotations(num) 生成数的所有循环排列。
3. 使用 is_circular_prime(num) 判断每个循环排列是否为素数。
代码详解：
if num % i == 0:
return False
return True
# 找到 1 到 100 之间的所有亲密素数对
prime_pairs = []
previous_prime = None
for num in range(2, 101):
if is_prime(num):
if previous_prime and num - previous_prime == 2:
prime_pairs.append((previous_prime, num))
previous_prime = num
print("亲密素数对为：", prime_pairs)
def is_prime(num):
if num < 2:
return False
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
return False
return True
def generate_rotations(num):
"""生成所有循环排列"""
rotations = []
s = str(num)
for i in range(len(s)):
rotated = int(s[i:] + s[:i])
rotations.append(rotated)
return rotations
def is_circular_prime(num):
"""判断是否为循环素数"""
for rotation in generate_rotations(num):
if not is_prime(rotation):
return False
return True
# 找出 1 到 100 之间的循环素数
circular_primes = [num for num in range(1, 101) if is_circular_prime(num)]
print("循环素数有：", circular_primes)

---

<!-- p.74 -->

4. 计算“最小公倍数数列”
题目：编写函数 gcd(a, b) 计算两个数的最大公约数，编写函数 lcm(a, b) 计算两个数的最小公倍
数，再编写 lcm_list(numbers) 计算一个整数列表的最小公倍数。测试 lcm_list 函数求 [4, 5,
12, 15] 的最小公倍数。
思路分析：
1. 使用欧几里得算法在 gcd 中计算最大公约数。
2. 使用公式 lcm(a, b) = a * b / gcd(a, b) 在 lcm 中计算最小公倍数。
3. 使用 reduce 和 lcm 计算列表的最小公倍数。
代码详解：
5. 判断“完全平方回文数”
题目：完全平方回文数是指一个数字的平方是回文数。例如，11 是完全平方回文数，因为 (11^2 =
121)，而 121 是回文数。编写函数 is_palindrome(num) 判断一个数是否为回文数，编写函数
is_square_palindrome(num) 判断一个数是否为完全平方回文数，输出 1 到 100 之间的所有完全平方
回文数。
思路分析：
1. 使用字符串反转在 is_palindrome(num) 中判断回文数。
2. 使用 is_square_palindrome(num) 判断一个数的平方是否为回文数。
3. 遍历 1 到 100，找出所有完全平方回文数。
代码详解：
from functools import reduce
def gcd(a, b):
"""计算最大公约数"""
while b:
a, b = b, a % b
return a
def lcm(a, b):
"""计算最小公倍数"""
return a * b // gcd(a, b)
def lcm_list(numbers):
"""计算列表中所有数字的最小公倍数"""
return reduce(lcm, numbers)
# 测试列表的最小公倍数
numbers = [4, 5, 12, 15]
result = lcm_list(numbers)
print("列表 [4, 5, 12, 15] 的最小公倍数是：", result)

---

<!-- p.75 -->

6. 查找“素数回文三角数”
题目：素数回文三角数是指同时满足以下条件的数字：
1. 该数字是素数。
2. 该数字是回文数（正向和反向相同）。
3. 该数字是三角数，三角数的公式为 n * (n + 1) / 2 。
请编写函数 is_prime(num) 、 is_palindrome(num) 和 is_triangle_number(num) 来判断一个数
是否满足这三个条件，并找出 1 到 10000 之间的所有素数回文三角数。
思路分析：
1. 使用 is_prime(num) 判断是否为素数。
2. 使用 is_palindrome(num) 判断是否为回文数。
3. 使用 is_triangle_number(num) 判断是否为三角数，检查是否符合三角数公式。
4. 遍历 1 到 10000 的数，筛选出符合所有条件的数字。
代码详解：
def is_palindrome(num):
"""判断一个数是否是回文数"""
return str(num) == str(num)[::-1]
def is_square_palindrome(num):
"""判断一个数的平方是否是回文数"""
square = num ** 2
return is_palindrome(square)
# 找出 1 到 100 之间的完全平方回文数
square_palindromes = [num for num in range(1, 101) if is_square_palindrome(num)]
print("完全平方回文数有：", square_palindromes)
def is_prime(num):
"""判断是否为素数"""
if num < 2:
return False
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
return False
return True
def is_palindrome(num):
"""判断是否为回文数"""
return str(num) == str(num)[::-1]
def is_triangle_number(num):
"""判断是否为三角数"""
n = (-1 + (1 + 8 * num) ** 0.5) / 2
return n.is_integer()
# 找出 1 到 10000 之间的素数回文三角数
result = []
for i in range(1, 10001):
if is_prime(i) and is_palindrome(i) and is_triangle_number(i):
result.append(i)

---

<!-- p.76 -->

7. 查找满足特定“数字和”的数字
题目：找出 100 到 999 之间所有的三位数，使得：
1. 各个位数字之和等于 15。
2. 各个位数字之积等于 36。
请编写函数 digit_sum(num) 和 digit_product(num) 来分别计算一个数字的位数之和与位数之积，
并找出符合条件的三位数。
思路分析：
1. 定义 digit_sum(num) 和 digit_product(num) ，分别计算一个数的位数和与位数积。
2. 遍历 100 到 999，检查位数和为 15 且位数积为 36 的数。
代码详解：
8. 寻找满足条件的“质数方差对”
题目：找出 1 到 1000 之间所有的质数对 (p, q)，使得 |p - q| 的平方等于 p + q 。即满足条件 |p -
q|^2 = p + q 。
思路分析：
1. 使用 is_prime(num) 判断质数。
2. 遍历 1 到 1000 中的质数对，检查是否满足 |p - q|^2 = p + q 。
3. 使用条件判断进行筛选，确保每对只输出一次。
代码详解：
print("素数回文三角数有：", result)
def digit_sum(num):
"""返回数字的位数和"""
return sum(int(d) for d in str(num))
def digit_product(num):
"""返回数字的位数积"""
product = 1
for d in str(num):
product *= int(d)
return product
# 找出满足条件的三位数
result = []
for num in range(100, 1000):
if digit_sum(num) == 15 and digit_product(num) == 36:
result.append(num)
print("满足条件的三位数有：", result)
def is_prime(num):
"""判断是否为素数"""
if num < 2:

---

<!-- p.77 -->

9. 查找“数位奇偶相反”的数字
题目：找出 1000 到 9999 之间所有四位数，使得：
1. 数字的奇数位（从左到右的第 1 位和第 3 位）为偶数。
2. 数字的偶数位（第 2 位和第 4 位）为奇数。
思路分析：
1. 使用整除和取余操作提取各个数位。
2. 检查奇数位是否为偶数，偶数位是否为奇数。
3. 遍历四位数范围，筛选符合条件的数字。
代码详解：
10. 检查“等差质数序列”
题目：找出 1 到 100 之间所有长度为 3 的等差质数序列 (p, q, r)，其中 p < q < r。即满足 q - p = r -
q ，且 p、q、r 均为素数。
思路分析：
1. 使用 is_prime(num) 函数判断质数。
return False
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
return False
return True
# 找出 1 到 1000 之间的所有质数方差对
prime_pairs = []
primes = [i for i in range(1, 1001) if is_prime(i)]
for i in range(len(primes)):
for j in range(i + 1, len(primes)):
p, q = primes[i], primes[j]
if (abs(p - q) ** 2) == (p + q):
prime_pairs.append((p, q))
print("满足条件的质数方差对有：", prime_pairs)
# 找出满足条件的四位数
result = []
for num in range(1000, 10000):
thousands = num // 1000 # 第一位（奇数位）
hundreds = (num // 100) % 10 # 第二位（偶数位）
tens = (num // 10) % 10 # 第三位（奇数位）
units = num % 10 # 第四位（偶数位）
if thousands % 2 == 0 and tens % 2 == 0 and hundreds % 2 == 1 and units % 2
== 1:
result.append(num)
print("满足条件的四位数有：", result)

---

<!-- p.78 -->

2. 使用嵌套循环枚举质数序列 (p, q, r)。
3. 检查是否满足等差条件 q - p = r - q 。
代码详解：
11. 检查“连续回文质数对”
题目：找出 1 到 1000 之间的所有回文质数对 (p, q) ，使得 p < q 且 q 是 p 的下一个回文质数。
思路分析：
1. 使用 is_prime(num) 和 is_palindrome(num) 判断质数和回文数。
2. 找到 1 到 1000 的所有回文质数，并检查是否连续。
3. 将符合条件的回文质数对存储在列表中。
代码详解：
def is_prime(num):
"""判断是否为素数"""
if num < 2:
return False
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
return False
return True
# 找出满足条件的等差质数序列
result = []
primes = [i for i in range(1, 101) if is_prime(i)]
for i in range(len(primes) - 2):
for j in range(i + 1, len(primes) - 1):
for k in range(j + 1, len(primes)):
p, q, r = primes[i], primes[j], primes[k]
if q - p == r - q:
result.append((p, q, r))
print("满足条件的等差质数序列有：", result)
def is_prime(num):
"""判断是否为素数"""
if num < 2:
return False
for i in range(2, int(num ** 0.5) + 1):
if num % i == 0:
return False
return True
def is_palindrome(num):
"""判断是否为回文数"""
return str(num) == str(num)[::-1]
# 找出 1 到 1000 之间所有连续回文质数对
result
= []

---

<!-- p.79 -->

21- 生成式
21.1 列表生成式（List Comprehension） - 掌握
列表生成式是一种简洁的语法，用于基于已有的可迭代对象（如列表、元组、字符串等）快速生成新的
列表。它可以替代传统的 for 循环来创建列表，使代码更简洁易读。
基本语法
表达式：指定每个元素在列表中的值，通常是一个运算、函数或变量。
变量：用于接收每次迭代的元素。
条件（可选）：为列表生成式添加一个过滤条件，只有满足条件的元素才会包含在新列表中。
示例 1：生成平方数列表
生成 1 到 10 的平方数列表。
示例 2：带条件的列表生成式
生成 1 到 20 中的偶数列表。
示例 3：嵌套循环的列表生成式
生成一个乘法表的列表。
palindromic_primes = [num for num in range(1, 1001) if is_prime(num) and
is_palindrome(num)]
for i in range(len(palindromic_primes) - 1):
p, q = palindromic_primes[i], palindromic_primes[i + 1]
result.append((p, q))
print("连续回文质数对有：", result)
[表达式 for 变量 in 可迭代对象 if 条件]
squares = [x ** 2 for x in range(1, 11)]
print(squares) # 输出: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
evens = [x for x in range(1, 21) if x % 2 == 0]
print(evens) # 输出: [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
multiplication_table = [i * j for i in range(1, 4) for j in range(1, 4)]
print(multiplication_table) # 输出: [1, 2, 3, 2, 4, 6, 3, 6, 9]

---

<!-- p.80 -->

21.2 字典生成式（Dictionary Comprehension） - 掌握
字典生成式用于基于可迭代对象生成一个新的字典。它的语法与列表生成式类似，但生成的是键值对的
字典，而不是列表。
基本语法
键表达式：生成字典中每个键的值。
值表达式：生成字典中每个键对应的值。
条件（可选）：用于过滤键值对，只有满足条件的元素才会包含在字典中。
示例 1：生成数字平方的字典
生成一个字典，键为 1 到 5 的数字，值为它们的平方。
示例 2：使用条件的字典生成式
生成一个字典，键为 1 到 10 的数字，值为 "偶数" 或 "奇数"。
示例 3：字典生成式处理两个列表
使用两个列表生成字典，其中一个列表提供键，另一个提供值。
21.3 元组生成式（Tuple Comprehension） - 掌握
严格来说，Python 并没有元组生成式，因为括号 () 被优先解释为生成器表达式。但我们可以通过将生
成器表达式转换为 tuple() 来实现类似元组生成式的效果。生成器表达式用于生成一个惰性求值的生
成器对象，可以减少内存占用。
基本语法
表达式：指定每个元素在生成器中的值。
变量：用于接收每次迭代的元素。
条件（可选）：用于过滤元素，只有满足条件的元素才会包含在生成器中。
{键表达式: 值表达式 for 变量 in 可迭代对象 if 条件}
squares_dict = {x: x ** 2 for x in range(1, 6)}
print(squares_dict) # 输出: {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
parity_dict = {x: "偶数" if x % 2 == 0 else "奇数" for x in range(1, 11)}
print(parity_dict)
# 输出: {1: '奇数', 2: '偶数', 3: '奇数', 4: '偶数', 5: '奇数', 6: '偶数', 7: '奇数',
8: '偶数', 9: '奇数', 10: '偶数'}
keys = ["a", "b", "c"]
values = [1, 2, 3]
combined_dict = {k: v for k, v in zip(keys, values)}
print(combined_dict) # 输出: {'a': 1, 'b': 2, 'c': 3}
(表达式 for 变量 in 可迭代对象 if 条件)

---

<!-- p.81 -->

示例 1：生成平方数的元组
生成 1 到 10 的平方数元组。
示例 2：带条件的生成器表达式转换为元组
生成 1 到 20 的偶数元组。
示例 3：生成嵌套元组
生成乘法表的嵌套元组。
21.4 生成式的优缺点（了解）
优点
1. 简洁高效：生成式使用一行代码创建数据结构，比传统的循环和条件判断更简洁。
2. 可读性高：生成式语法直观清晰，减少代码行数，提升代码的可读性。
3. 节省内存：生成器表达式使用惰性求值，不会立即生成所有元素，适合处理大数据量。
缺点
1. 复杂性限制：生成式适合简单的逻辑，过于复杂的表达式会降低可读性。
2. 调试难度：生成式中嵌套条件判断或多重循环时，调试较为困难。
3. 生成器的单次迭代：生成器表达式只能被迭代一次，需注意使用场景。
22- 文件读写
22.1 文件的打开（掌握）
在 Python 中，文件可以通过内置的 open() 函数来打开。 open() 函数接受两个主要参数：文件路径
和文件模式。
基本语法
squares_tuple = tuple(x ** 2 for x in range(1, 11))
print(squares_tuple) # 输出: (1, 4, 9, 16, 25, 36, 49, 64, 81, 100)
evens_tuple = tuple(x for x in range(1, 21) if x % 2 == 0)
print(evens_tuple) # 输出: (2, 4, 6, 8, 10, 12, 14, 16, 18, 20)
multiplication_table = tuple((i, j, i * j) for i in range(1, 4) for j in
range(1, 4))
print(multiplication_table)
# 输出: ((1, 1, 1), (1, 2, 2), (1, 3, 3), (2, 1, 2), (2, 2, 4), (2, 3, 6), (3, 1,
3), (3, 2, 6), (3, 3, 9))
file = open("文件路径", "模式")

---

<!-- p.82 -->

模式 含义
'r' 读取模式（默认值），文件必须存在，读取内容。
'w' 写入模式，若文件已存在则清空文件，若不存在则创建新文件。
'a' 追加模式，在文件末尾添加内容。若文件不存在则创建新文件。
'b' 以二进制模式读写文件，用 'rb' 、 'wb' 等组合形式。
'r+' 读写模式，可以同时读取和写入。
'w+' 读写模式，文件存在则清空，不存在则创建。
'a+' 读写模式，在文件末尾追加内容，不存在则创建。
文件模式
常用的文件模式如下：
示例：打开文件进行读取
22.2 文件的读取（掌握）
Python 提供多种方法来读取文件内容。常用的读取方法有 read() 、 readline() 和 readlines() 。
22.2.1 read() 读取整个文件内容
示例：
22.2.2 readline() 逐行读取
示例：
file = open("example.txt", "r")
# 执行文件读取或其他操作
file.close() # 关闭文件
file = open("example.txt", "r")
content = file.read()
print(content) # 输出整个文件内容
file.close()
file = open("example.txt", "r")
line = file.readline() # 读取文件的第一行
while line:
print(line, end="") # 打印每行内容
line = file.readline() # 继续读取下一行
file.close()

---

<!-- p.83 -->

22.2.3 readlines() 读取所有行，返回列表
示例：
22.3 文件的写入（掌握）
使用 'w' 模式或 'w+' 模式可以将内容写入文件，注意 'w' 模式会清空文件内容。写入可以通过
write() 或 writelines() 方法实现。
21.3.1 write() 写入字符串
示例：
22.3.2 writelines() 写入多行
示例：
22.4 文件的追加（掌握）
使用 'a' 模式可以在文件末尾追加内容。追加写入不会清空文件内容，而是在已有内容的末尾追加。
示例：
22.5 使用 with 语句自动管理文件（掌握）
在文件操作中，手动关闭文件是必须的，但有时可能会忘记使用 close() 。使用 with 语句可以确保
文件操作完成后自动关闭文件，即使在执行过程中发生错误。
file = open("example.txt", "r")
lines = file.readlines() # 读取所有行，返回列表
for line in lines:
print(line, end="") # 打印每行内容
file.close()
file = open("example.txt", "w")
file.write("Hello, world!\n") # 写入字符串
file.write("Python 文件写入示例。\n")
file.close()
file = open("example.txt", "w")
lines = ["第一行\n", "第二行\n", "第三行\n"]
file.writelines(lines) # 写入多行内容
file.close()
file = open("example.txt", "a")
file.write("这是追加的一行。\n") # 在文件末尾追加
file.close()

---

<!-- p.84 -->

示例：使用 with 语句读取文件
示例：使用 with 语句写入文件
22.6 文件指针的移动（了解）
文件指针用于指示当前读写的位置。使用 seek() 和 tell() 可以控制和获取指针的位置。
22.6.1 seek(offset, whence) 移动指针
参数：
offset ：指针移动的偏移量。
whence ：移动的起始位置（ 0 表示文件开头， 1 表示当前位置， 2 表示文件末尾）。
示例：
22.6.2 tell() 获取当前指针位置
示例：
22.7 文件的其他操作（了解）
Python 提供了一些内置的文件操作方法，如 os 模块中的 remove() 、 rename() 、 exists() 等，用
于对文件进行删除、重命名、检查是否存在等操作。
删除文件
使用 os.remove() 删除指定文件。
with open("example.txt", "r") as file:
content = file.read()
print(content)
# 此时文件已自动关闭
with open("example.txt", "w") as file:
file.write("使用 with 语句写入内容。\n")
# 文件已自动关闭
with open("example.txt", "r") as file:
file.seek(5) # 将指针移动到文件的第 5 个字节
print(file.read()) # 从第 5 个字节开始读取
with open("example.txt", "r") as file:
print(file.tell()) # 输出指针当前位置
file.read(5) # 读取 5 个字节
print(file.tell()) # 输出新的指针位置
import os
os.remove("example.txt") # 删除文件 example.txt

---

<!-- p.85 -->

重命名文件
使用 os.rename() 重命名文件。
检查文件是否存在
使用 os.path.exists() 检查文件是否存在。
22.8 二进制文件的读写（了解）
对于非文本文件（如图片、视频、音频等），需要使用二进制模式读写，以避免编码问题。使用模式
'rb' 读取二进制文件，使用 'wb' 写入二进制文件。
示例：读取二进制文件
示例：写入二进制文件
22.9 文件读写的常见问题（掌握）
1. 忘记关闭文件：在文件操作结束后要记得关闭文件，或使用 with 语句自动管理文件。
2. 文件路径错误：检查文件路径是否正确，可以使用绝对路径或相对路径。
3. 文件编码问题：如果文件包含非 ASCII 字符，建议在打开文件时指定编码，如
open("example.txt", "r", encoding="utf-8") 。
4. 文件不存在：在打开文件之前检查文件是否存在，避免 FileNotFoundError 错误。
5. 文件权限错误：确保对文件具有相应的读写权限，否则可能会遇到 PermissionError 错误。
23- 面向对象
23.1 面向对象编程的基本概念（掌握）
面向对象编程（OOP）是一种编程范式，它将数据和操作数据的方法封装在一起，称之为对象。Python
是一门面向对象语言，OOP 中的关键概念有以下几个：
类（Class）：类是创建对象的模板或蓝图，它定义了对象的属性和方法。
对象（Object）：对象是类的实例，通过类来创建。
os.rename("old_name.txt", "new_name.txt") # 重命名文件
if os.path.exists("example.txt"):
print("文件存在")
else:
print("文件不存在")
with open("example.jpg", "rb") as file:
content = file.read()
print(content) # 输出二进制内容
with open("example_copy.jpg", "wb") as file:
file.write(content) # 将读取的二进制内容写入新文件

---

<!-- p.86 -->

属性（Attribute）：属性是对象的特征或数据，通常是类中定义的变量。
方法（Method）：方法是对象的行为或操作，通常是类中定义的函数。
示例：定义一个简单的类
23.2 类的定义和实例化（掌握）
在 Python 中，使用 class 关键字定义类，类名通常遵循首字母大写的命名约定。定义完类后，通过调
用类名并传入必要的参数来创建类的实例（即对象）。
定义类：
实例化对象：
示例
class Dog:
# 类属性
species = "Canis lupus"
# 初始化方法（构造函数）
def __init__(self, name, age):
self.name = name # 实例属性
self.age = age # 实例属性
# 实例方法
def bark(self):
print(f"{self.name} says Woof!")
# 创建对象
my_dog = Dog("Buddy", 3)
print(my_dog.name) # 输出: Buddy
my_dog.bark() # 输出: Buddy says Woof!
class ClassName:
# 类的内容（属性和方法）
object_name = ClassName(parameters)
class Car:
def __init__(self, make, model):
self.make = make # 实例属性
self.model = model
my_car = Car("Toyota", "Corolla")
print(my_car.make) # 输出: Toyota
print(my_car.model) # 输出: Corolla

---

<!-- p.87 -->

23.3 __init__ 方法（构造函数）（掌握）
__init__ 方法是类的构造函数，在创建对象时自动调用，用于初始化对象的属性。它通常接收参数来
为属性赋初始值。
定义 __init__ 方法：
示例
23.4 实例属性和类属性（掌握）
实例属性：每个对象独立拥有的属性，由 self 关键字定义。实例属性在不同的对象中可以拥有不
同的值。
类属性：类本身的属性，不属于任何一个特定的对象，由类名直接访问。类属性在所有对象中共
享。
示例
23.5 实例方法和类方法（掌握）
实例方法：实例方法是作用于对象的方法，第一个参数为 self ，表示该方法属于对象，可以访问
对象的属性。
类方法：类方法由 @classmethod 装饰器定义，第一个参数为 cls ，表示该方法属于类，可以访
问类属性。类方法通常用于创建或操作类级别的数据。
def __init__(self, 参数1, 参数2):
self.属性1 = 参数1
self.属性2 = 参数2
class Book:
def __init__(self, title, author):
self.title = title
self.author = author
my_book = Book("1984", "George Orwell")
print(my_book.title) # 输出: 1984
print(my_book.author) # 输出: George Orwell
class Animal:
species = "Mammal" # 类属性
def __init__(self, name):
self.name = name # 实例属性
a1 = Animal("Lion")
a2 = Animal("Tiger")
print(a1.species) # 输出: Mammal
print(a2.species) # 输出: Mammal
print(a1.name) # 输出: Lion
print(a2.name) # 输出: Tiger

---

<!-- p.88 -->

示例
23.6 静态方法（掌握）
静态方法不需要传入 self 或 cls 参数，通常不与类或对象的属性进行交互，常用于工具方法。使用
@staticmethod 装饰器定义静态方法。
示例
23.7 封装与私有属性（掌握）
封装是 OOP 的核心思想之一，通过将对象的内部数据隐藏起来，只允许通过特定方法访问。Python 使
用双下划线前缀 __ 将属性定义为私有属性，限制外部直接访问。
示例
class Circle:
pi = 3.14 # 类属性
def __init__(self, radius):
self.radius = radius # 实例属性
def area(self): # 实例方法
return Circle.pi * (self.radius ** 2)
@classmethod
def set_pi(cls, new_pi): # 类方法
cls.pi = new_pi
c1 = Circle(5)
print(c1.area()) # 输出: 78.5
Circle.set_pi(3.1416)
print(c1.area()) # 输出: 78.54（使用新值 3.1416）
class Math:
@staticmethod
def add(x, y):
return x + y
result = Math.add(5, 3)
print(result) # 输出: 8
class Account:
def __init__(self, owner, balance):
self.owner = owner
self.__balance = balance # 私有属性
def deposit(self, amount):
if amount > 0:
self.__balance += amount
def get_balance(self):

---

<!-- p.89 -->

23.8 继承（掌握）
继承允许我们创建一个新的类，并从现有类中继承属性和方法。继承使代码重用更高效，新类称为子
类，继承的类称为父类或超类。
示例
23.9 方法重写（掌握）
方法重写（Override）允许子类重写父类的方法。子类重写的方法可以覆盖父类的方法，实现不同的功
能。
示例
23.10 多态（掌握）
多态是指对象在不同的场景中表现出不同的行为。Python 的多态性允许使用相同的方法名调用不同类的
实例，而不关心实例的具体类型。
return self.__balance
account = Account("Alice", 1000)
account.deposit(500)
print(account.get_balance()) # 输出: 1500
# print(account.__balance) # 访问报错，私有属性
class Animal:
def speak(self):
print("Animal speaks")
class Dog(Animal): # Dog 类继承 Animal 类
def bark(self):
print("Dog barks")
dog = Dog()
dog.speak() # 调用父类方法，输出: Animal speaks
dog.bark() # 调用子类方法，输出: Dog barks
class Animal:
def speak(self):
print("Animal speaks")
class Dog(Animal):
def speak(self): # 重写父类方法
print("Dog barks")
dog = Dog()
dog.speak() # 输出: Dog barks

---

<!-- p.90 -->

示例
23.11 面向对象的优势（了解）
1. 封装：将数据和行为封装在一起，提高代码安全性。
2. 继承：实现代码重用，减少重复代码。
3. 多态：同一方法在不同对象中表现出不同的行为，提高代码的灵活性。
4. 抽象：隐藏复杂实现，暴露简单接口，提高代码的可维护性。
24- 面向对象综合案例
案例 1：银行账户系统
需求：
1. 创建一个 BankAccount 类，用于管理银行账户。
2. 该类需要包含以下功能：
开户：初始化账户名、账户余额和账户类型（如储蓄、支票）。
存款：向账户中添加指定金额。
取款：从账户中取出指定金额，余额不足时给出警告。
查询余额：显示当前余额。
思路分析：
BankAccount 类包含初始化方法 __init__ 来设置账户名称、余额和账户类型。
定义 deposit 和 withdraw 方法分别用于存款和取款，确保取款时余额足够。
定义 get_balance 方法用于查询余额。
代码实现：
class Animal:
def speak(self):
print("Animal speaks")
class Dog(Animal):
def speak(self):
print("Dog barks")
class Cat(Animal):
def speak(self):
print("Cat meows")
animals = [Dog(), Cat()]
for animal in animals:
animal.speak() # 输出 Dog barks 和 Cat meows
class BankAccount:
def __init__(self, account_name, initial_balance=0, account_type="Savings"):
self.account_name = account_name
self.balance = initial_balance
self.account_type = account_type

---

<!-- p.91 -->

案例 2：图书馆系统
需求：
1. 创建一个 Book 类，包含书籍的基本信息（如标题、作者、ISBN 编号）。
2. 创建一个 Library 类，用于管理图书馆的藏书和借阅记录。
3. Library 类需要包含以下功能：
添加书籍：将书籍添加到藏书列表。
借书：用户可以借阅指定书籍，若该书已被借出则提示不可用。
归还书籍：将书籍归还到图书馆。
思路分析：
Book 类包含书籍的基本信息，如标题、作者和 ISBN 编号。
Library 类包含一个 books 字典，用于记录图书馆的藏书信息，书籍的可用状态（ True 表示可
用， False 表示已借出）。
在 Library 类中定义 add_book 、 borrow_book 和 return_book 方法来管理书籍的借阅和归
还。
代码实现：
def deposit(self, amount):
if amount > 0:
self.balance += amount
print(f"存入 {amount} 元。当前余额：{self.balance} 元")
else:
print("存款金额必须为正数。")
def withdraw(self, amount):
if amount > self.balance:
print("余额不足，无法取款。")
elif amount > 0:
self.balance -= amount
print(f"取出 {amount} 元。当前余额：{self.balance} 元")
else:
print("取款金额必须为正数。")
def get_balance(self):
print(f"{self.account_name} 的当前余额：{self.balance} 元")
# 测试
account = BankAccount("Alice", 1000)
account.deposit(500)
account.withdraw(300)
account.get_balance()
account.withdraw(1500) # 余额不足
class Book:
def __init__(self, title, author, isbn):
self.title = title
self.author = author
self.isbn = isbn
class Library:

---

<!-- p.92 -->

案例 3：员工管理系统
需求：
1. 创建一个基类 Employee ，包含员工的基本信息（如姓名和薪资）。
2. 创建两个子类 Manager 和 Developer ，继承 Employee ，并在子类中实现特定的方法和属性。
3. 需要提供以下功能：
Manager 类可以管理一个员工列表。
Developer 类可以记录其特定的编程语言。
打印每个员工的信息，区分不同员工类型。
思路分析：
def __init__(self):
self.books = {}
def add_book(self, book):
if book.isbn not in self.books:
self.books[book.isbn] = {"book": book, "available": True}
print(f"添加书籍：《{book.title}》")
else:
print(f"书籍《{book.title}》已存在于图书馆。")
def borrow_book(self, isbn):
if isbn in self.books:
if self.books[isbn]["available"]:
self.books[isbn]["available"] = False
print(f"成功借出书籍：《{self.books[isbn]['book'].title}》")
else:
print("该书籍已被借出。")
else:
print("该书籍不存在于图书馆。")
def return_book(self, isbn):
if isbn in self.books:
if not self.books[isbn]["available"]:
self.books[isbn]["available"] = True
print(f"成功归还书籍：《{self.books[isbn]['book'].title}》")
else:
print("该书籍已经在馆。")
else:
print("该书籍不存在于图书馆。")
# 测试
library = Library()
book1 = Book("Python Basics", "Author A", "ISBN001")
book2 = Book("Data Science", "Author B", "ISBN002")
library.add_book(book1)
library.add_book(book2)
library.borrow_book("ISBN001")
library.borrow_book("ISBN001") # 已被借出
library.return_book("ISBN001")
library.borrow_book("ISBN003") # 不存在的书籍

---

<!-- p.93 -->

Employee 类作为基类，包含基本信息属性和显示信息的方法。
Manager 类继承自 Employee ，包含一个员工列表，并可添加管理的员工。
Developer 类继承自 Employee ，包含一个记录编程语言的属性。
代码实现：
25- 数据类型转换
class Employee:
def __init__(self, name, salary):
self.name = name
self.salary = salary
def display_info(self):
print(f"员工姓名: {self.name}, 薪资: {self.salary}")
class Manager(Employee):
def __init__(self, name, salary):
super().__init__(name, salary)
self.employees = []
def add_employee(self, employee):
if isinstance(employee, Employee) and employee not in self.employees:
self.employees.append(employee)
print(f"{self.name} 现在管理员工 {employee.name}")
def display_info(self):
super().display_info()
print("管理的员工:")
for emp in self.employees:
print(f"- {emp.name}")
class Developer(Employee):
def __init__(self, name, salary, language):
super().__init__(name, salary)
self.language = language
def display_info(self):
super().display_info()
print(f"编程语言: {self.language}")
# 测试
manager = Manager("Alice", 100000)
dev1 = Developer("Bob", 80000, "Python")
dev2 = Developer("Charlie", 85000, "JavaScript")
manager.add_employee(dev1)
manager.add_employee(dev2)
manager.display_info()
dev1.display_info()
dev2.display_info()

---

<!-- p.94 -->

函数 描述
int(x) 将 x 转换为整数
float(x) 将 x 转换为浮点数
str(x) 将 x 转换为字符串
list(x) 将 x 转换为列表
tuple(x) 将 x 转换为元组
set(x) 将 x 转换为集合
dict(x) 将 x 转换为字典（需满足特定结构）
25.1 数据类型转换概述（掌握）
数据类型转换指的是将一个数据类型转换为另一个数据类型。例如，将整数转换为浮点数，将字符串转
换为列表等。Python 提供了多种内置函数来实现不同的数据类型转换。
25.2 常见的数据类型转换方法（掌握）
Python 提供的基本数据类型转换函数如下：
25.3 数字类型转换（掌握）
Python 中支持整数和浮点数的转换，可以通过 int() 和 float() 函数实现。
25.3.1 整数和浮点数转换
示例：
25.3.2 字符串和数字的转换
字符串转整数：
字符串转浮点数：
# 将浮点数转换为整数
num1 = 3.14
int_num1 = int(num1) # 输出: 3
# 将整数转换为浮点数
num2 = 5
float_num2 = float(num2) # 输出: 5.0
str_num = "123"
int_num = int(str_num) # 输出: 123
str_float = "3.14"
float_num = float(str_float) # 输出: 3.14

---

<!-- p.95 -->

数字转字符串：
25.4 字符串与列表/元组的转换（掌握）
字符串、列表和元组之间的转换方法主要依靠 list() 、 tuple() 和 join() 函数。
25.4.1 字符串转列表和元组
字符串转列表：每个字符将成为列表的一个元素。
字符串转元组：使用 tuple() 将字符串转换为元组。
25.4.2 列表/元组转字符串
列表转字符串：使用 join() 方法将列表中的元素合并为字符串。
元组转字符串：同样使用 join() 方法。
25.5 列表、元组、集合的互相转换（掌握）
可以使用 list() 、 tuple() 和 set() 函数在列表、元组和集合之间进行转换。
24.5.1 列表、元组、集合的转换
列表转元组：
列表转集合：
元组转列表：
num = 456
str_num = str(num) # 输出: "456"
text = "hello"
text_list = list(text) # 输出: ['h', 'e', 'l', 'l', 'o']
text_tuple = tuple(text) # 输出: ('h', 'e', 'l', 'l', 'o')
words = ['Python', 'is', 'fun']
sentence = ' '.join(words) # 输出: "Python is fun"
chars = ('P', 'y', 't', 'h', 'o', 'n')
word = ''.join(chars) # 输出: "Python"
fruits = ['apple', 'banana', 'cherry']
fruits_tuple = tuple(fruits) # 输出: ('apple', 'banana', 'cherry')
fruits_set = set(fruits) # 输出: {'apple', 'banana', 'cherry'}
fruits_list = list(fruits_tuple) # 输出: ['apple', 'banana', 'cherry']

---

<!-- p.96 -->

集合转列表：
25.6 字典的转换（掌握）
字典的键和值可以分别转换为列表、元组或集合，字典本身可以通过满足一定结构的列表或元组进行转
换。
25.6.1 字典转列表/元组/集合
字典键转换为列表：
字典值转换为列表：
字典键值对转换为元组列表：
25.6.2 列表/元组转字典
列表转字典：列表中的元素需为二元组。
元组转字典：与列表转字典相同，要求元组内元素为二元组。
25.7 常见数据类型转换示例（掌握）
示例 1：混合数据类型列表转字符串
将包含多个不同数据类型的列表元素合并成字符串。
set_to_list = list(fruits_set) # 输出: ['apple', 'banana', 'cherry']
person = {'name': 'Alice', 'age': 25}
keys_list = list(person.keys()) # 输出: ['name', 'age']
values_list = list(person.values()) # 输出: ['Alice', 25]
items_list = list(person.items()) # 输出: [('name', 'Alice'), ('age', 25)]
items = [('name', 'Bob'), ('age', 30)]
person_dict = dict(items) # 输出: {'name': 'Bob', 'age': 30}
items_tuple = (('name', 'Charlie'), ('age', 35))
person_dict = dict(items_tuple) # 输出: {'name': 'Charlie', 'age': 35}
data = [1, 'apple', 3.14]
string_data = ' | '.join(map(str, data))
print(string_data) # 输出: "1 | apple | 3.14"

---

<!-- p.97 -->

示例 2：字符串列表转整数列表
将一个包含数字字符串的列表转换为整数列表。
示例 3：将嵌套列表转换为字典
将嵌套列表（每个子列表包含键值对）转换为字典。
25.8 数据类型转换的注意事项（掌握）
1. 转换条件：并非所有数据类型都可以互相转换，如将非数值字符串转换为数字会报错。
2. 精度损失：浮点数转换为整数时会丢失小数部分。
3. 可变与不可变：列表、字典和集合是可变类型，元组和字符串是不可变类型。数据转换时要注意特
性变化。
4. 数据丢失：集合的元素是唯一的，将包含重复元素的列表转换为集合会自动去重。
二，常用库(共15个)
1，os模块
str_nums = ["10", "20", "30"]
int_nums = list(map(int, str_nums))
print(int_nums) # 输出: [10, 20, 30]
data = [["name", "Alice"], ["age", 28], ["city", "New York"]]
data_dict = dict(data)
print(data_dict) # 输出: {'name': 'Alice', 'age': 28, 'city': 'New York'}
int("hello") # ValueError: invalid literal for int()
int(3.9) # 输出: 3
list_to_set = set([1, 2, 2, 3]) # 输出: {1, 2, 3}
import os
# 判断文件是否存在
os.path.exists() # 判断文件或者文件夹是否存在，返回布尔值
os.path.join() # 路径拼接
os.path.join(path1,path2,path3)
os.makedirs() # 创建文件夹
os.getcwd() # 获取当前工作目录，即当前python脚本工作的目录路径
os.chdir("dirname") # 改变当前脚本工作目录；相当于shell下cd
os.curdir # 返回当前目录: ('.')

---

<!-- p.98 -->

2，json模块
os.pardir # 获取当前目录的父目录字符串名：('..')
os.makedirs('dirname1/dirname2') # 可生成多层递归目录
os.removedirs('dirname1') # 若目录为空，则删除，并递归到上一级目录，如若也为空，则删除，
依此类推
os.mkdir('dirname') # 生成单级目录；相当于shell中mkdir dirname
os.rmdir('dirname') # 删除单级空目录，若目录不为空则无法删除，报错；相当于shell中rmdir
dirname
os.listdir('dirname') # 列出指定目录下的所有文件和子目录，包括隐藏文件，并以列表方式打印
os.remove() # 删除一个文件
os.rename("oldname","newname") # 重命名文件/目录
os.stat('path/filename') # 获取文件/目录信息
os.sep # 输出操作系统特定的路径分隔符，win下为"\\",Linux下为"/"
os.linesep # 输出当前平台使用的行终止符，win下为"\t\n",Linux下为"\n"
os.pathsep # 输出用于分割文件路径的字符串 win下为;,Linux下为:
os.name # 输出字符串指示当前使用平台。win->'nt'; Linux->'posix'
os.system("bash command") # 运行shell命令，直接显示
os.environ # 获取系统环境变量
os.path.abspath(path) # 返回path规范化的绝对路径
os.path.split(path) # 将path分割成目录和文件名二元组返回
os.path.dirname(path) # 返回path的目录。其实就是os.path.split(path)的第一个元素
os.path.basename(path) # 返回path最后的文件名。如何path以／或\结尾，那么就会返回空值。即
os.path.split(path)的第二个元素
os.path.exists(path) # 如果path存在，返回True；如果path不存在，返回False
os.path.isabs(path) # 如果path是绝对路径，返回True
os.path.isfile(path) # 如果path是一个存在的文件，返回True。否则返回False
os.path.isdir(path) #如果path是一个存在的目录，则返回True。否则返回False
os.path.join(path1[, path2[, ...]]) # 将多个路径组合后返回，第一个绝对路径之前的参数将被
忽略
os.path.getatime(path) # 返回path所指向的文件或者目录的最后存取时间
os.path.getmtime(path) # 返回path所指向的文件或者目录的最后修改时间
os.path.getsize(path) # 返回path的大小
## JSON格式兼容的是所有语言通用的数据类型，不能支持单一数据类型
# JSON ---------字典
dic = json.loads(s)
# 字典-----------JSON
s = json.dumps(dic)
import json
## 有时保存下来的中文数据打开后发现变成ASCII码，这是需要将ensure_ascii参数设置成False
data = {
'name' : 'name',
'age' : 20,
}
json_str = json.dumps(data,ensure_ascii=False)
# josn.dump
data = {
'name':'name',
'age':20,
}
#讲python编码成json放在那个文件里

---

<!-- p.99 -->

2.1 猴子补丁S
3，random模块
filename = 'a.txt'
with open (filename,'w') as f:
json.dump(data ,f)
## json.load
data = {
'name':'name',
'age':20
}
filename = 'a.txt'
with open (filename,'w') as f:
json.dump(data,f)
with open (filename) as f_:
print(json.load(f_))
### 在入扣文件处进行猴子补丁
import json
import ujson
def monkey_patch_json():
json.__name__ = 'ujson'
json.dumps = ujson.dumps
json.loads = ujson.loads
monkey_patch_json()
a = random.choice('abcdefghijklmn') # 参数也可以是个列表
a = "abcdefghijklmnop1234567890"
b = random.sample(a,3) # 随机取三个值，返回一个列表
num = random.randint(1,100)

---

<!-- p.100 -->

4，string模块
5，异常处理
5.1 错误类型
1，random.random() # 得到的是 0----1 之间的小数 -------------- 0.6400374661599008
2，random.randint(1,3) # 范围是 [1,3] 包头包尾
3，random.randrange(1,2) # 范围是 [1,3) 顾头不顾尾
4，random.chioce('abcdefghijklmn') # 参数也可以是个列表
5，random.sample(['a','b','c','d'],3) # 随机取三个值，返回一个列表
6，random.uniform(1,3) # 得到 1-------3 之间的浮点数
item = [1,2,3,4,5,6,7,8,9]
7，random.shuffle(item) # 洗牌，打乱顺序 [4, 1, 2, 9, 7, 5, 6, 3, 8]
string.ascii_letters # 返回小写字母大写字母字符串
# 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
string.ascii_uppercase # 返回大写字母的字符串
# 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
string.ascii_lowercase # 返回小写字母的字符串
# 'abcdefghijklmnopqrstuvwxyz'
string.punctuation # 打印特殊字符
# '!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'
string.digits # 打印数字
# '0123456789'
## 语法错误 SyntaxError
## 逻辑错误 NameError IndexError ZeroDivisionError ValueError
## 一种是语法上的错误SyntaxError，这种错误应该在程序运行前就修改正确
if
File "<stdin>", line 1
if
^
SyntaxError: invalid syntax
# -------------------------------------------------------------------------------
------------
# TypeError：数字类型无法与字符串类型相加
1+’2’
# ValueError：当字符串包含有非数字的值时，无法转成int类型
num=input(">>: ") #输入hello
int(num)
# NameError：引用了一个不存在的名字x
x

---

<!-- p.101 -->

5.1 逻辑错误两种处理方式
5.1.1 错误时可以预知的
5.1.2 错误时不可预知的
# IndexError：索引超出列表的限制
l=['egon','aa']
l[3]
# KeyError：引用了一个不存在的key
dic={'name':'egon'}
dic['age']
# AttributeError：引用的属性不存在
class Foo:
pass
Foo.x
# ZeroDivisionError：除数不能为0
1/0
age = input(">>:").strip()
if age.isdigit(): ## 可以用if 判断避免错误出现
age = int(age) ## age必须是数字，才能转换为int类型
if age > 18:
print("猜大了")
else:
print('猜小了')
## 只要抛出异常同级别的代码不会往下运行
try:
##有可能抛出异常的子代码块
except 异常类型1 as e:
pass
except 异常类型2 as e:
pass
....
else:
## 如果被检测的子代码块没有异常发生则运行else
finally:
## 无论有没有异常发生都会运行此代码
## ------------------------------------------------------------------------------
--------------
## 用法一
try:
print('11111111111')
l = ['aaa','bbbb']
l[3] ## 抛出异常IndexError，该码块同级别的后续代码不会运行

---

<!-- p.102 -->

print('222222222222222')
xxx
print('3333333333333333333')
dic = {'a':1}
dic['a']
print('end')
except IndexError as e:
print('异常处理了')
print(e)
except NameError as e:
print('异常处理了')
print(e)
## ---------------------------------------------------------------------------
-----------
# 用法二
print('start')
try:
print('11111111111')
l = ['aaa','bbbb']
l[3] ## 抛出异常IndexError，该码块同级别的后续代码不会运行
print('222222222222222')
# xxx
print('3333333333333333333')
dic = {'a':1}
dic['a']
print('end')
except (IndexError,NameError) as e:
print('异常处理了')
except KeyError as e:
print('字典的key不存在',e)
## --------------------------------------------------------------------------
----------------
## 用法三
## 万能异常
print('start')
try:
print('11111111111')
l = ['aaa','bbbb']
l[3] ## 抛出异常IndexError，该码块同级别的后续代码不会运行
print('222222222222222')
# xxx
print('3333333333333333333')
dic = {'a':1}
dic['a']
print('end')
except Exception as e: ## 万能异常，都能匹配上
print('万能异常')
## ------------------------------------------------------------------------------
----------
## 方法四
##tyr 不能跟 else 连用
try:
print('11111111111111')

---

<!-- p.103 -->

6，打码平台使用
print('33333333333')
print('2222222222222222222')
except Exception as e:
print('所有异常都能匹配到')
else:
print('==============>')
print('end...........')
## ------------------------------------------------------------------------------
------------
## 方法五
## finally 可以单独与try配合使用
print('start')
try:
print('11111111111')
l = ['aaa','bbbb']
l[3] ## 抛出异常IndexError，该码块同级别的后续代码不会运行
print('222222222222222')
xxx
print('3333333333333333333')
dic = {'a':1}
dic['a']
print('end')
finally:
## 应该把被检测代码中，回收系统化资源的代码放这里
print('我不处理异常，无论是否发生异常我都会运行')
import base64
import json
import requests
def base64_api(uname, pwd, img, typeid):
with open(img, 'rb') as f:
base64_data = base64.b64encode(f.read())
b64 = base64_data.decode()
data = {"username": uname, "password": pwd, "typeid": typeid, "image": b64}
result = json.loads(requests.post("http://api.ttshitu.com/predict",
json=data).text)
if result['success']:
return result["data"]["result"]
else:
#！！！！！！！注意：返回 人工不足等 错误情况 请加逻辑处理防止脚本卡死 继续重新 识别
return result["message"]
return ''
if __name__ == "__main__":
img_path = "./code.png"
result = base64_api(uname='xxxxx', pwd='xxxxx', img=img_path, typeid=3)
print(result)
import base64
import json

---

<!-- p.104 -->

7，时间模块
import requests
# 一、图片文字类型(默认 3 数英混合)：
# 1 : 纯数字
# 1001：纯数字2
# 2 : 纯英文
# 1002：纯英文2
# 3 : 数英混合
# 1003：数英混合2
# 4 : 闪动GIF
# 7 : 无感学习(独家)
# 11 : 计算题
# 1005: 快速计算题
# 16 : 汉字
# 32 : 通用文字识别(证件、单据)
# 66: 问答题
# 49 :recaptcha图片识别
# 二、图片旋转角度类型：
# 29 : 旋转类型
#
# 三、图片坐标点选类型：
# 19 : 1个坐标
# 20 : 3个坐标
# 21 : 3 ~ 5个坐标
# 22 : 5 ~ 8个坐标
# 27 : 1 ~ 4个坐标
# 48 : 轨迹类型
#
# 四、缺口识别
# 18 : 缺口识别（需要2张图 一张目标图一张缺口图）
# 33 : 单缺口识别（返回X轴坐标 只需要1张图）
# 五、拼图识别
# 53：拼图识别
def base64_api(uname, pwd, img, typeid):
with open(img, 'rb') as f:
base64_data = base64.b64encode(f.read())
b64 = base64_data.decode()
data = {"username": uname, "password": pwd, "typeid": typeid, "image": b64}
result = json.loads(requests.post("http://api.ttshitu.com/predict",
json=data).text)
if result['success']:
return result["data"]["result"]
else:
#！！！！！！！注意：返回 人工不足等 错误情况 请加逻辑处理防止脚本卡死 继续重新 识别
return result["message"]
return ""
if __name__ == "__main__":
img_path = "C:/Users/Administrator/Desktop/file.jpg"
result = base64_api(uname='你的账号', pwd='你的密码', img=img_path, typeid=3)
print(result)

---

<!-- p.105 -->

7.1 time 模块
7.2 datetime 模块
7.3 时间格式的转换
import time
# 时间戳 ： 从1970年到现在经过的秒数
time.time() # 时间戳---------用于计算
# 按照某种格式显示时间： 2020-03-30 11:11:11 AM || PM
time.strftime('%Y-%m-%d %H:%M:%S %p') # 2023-06-27 14:24:38 PM
time.strftime('%Y-%m-%d %X') # 2023-06-27 14:24:38
#结构化时间
res = time.localtime() ## --------------获取年月日
print(res) ## time.struct_time(tm_year=2023, tm_mon=6, tm_mday=27, tm_hour=14,
tm_min=26, tm_sec=17, tm_wday=1, tm_yday=178, tm_isdst=0)
print(res.tm_year) ## 年
print(res.tm_mon) ## 月
print(res.tm_mday) ## 日
print(res.tm_hour) ## 小时
print(res.tm_min) ## 分钟
print(res.tm_sec) ## 秒
print(res.tm_wday)
print(res.tm_yday)
print(res.tm_isdst)
import datetime
datetime.datetime.now() ## 2023-06-27 14:38:31.929938
datetime.datetime.now() + datetime.timedelta(days = 3) ## 三天后的时间 2023-06-30
14:40:55.794329
# 参数有 days || secondes || weeks || hours || minutes
# days = 3 || -3 参数可以 为负数
import time
1，时间戳 <-----------------> 结构化时间
# 结构化时间 -------------------------> 时间戳
s_time = time.localtime() # 结构化时间
res = time.mktime(s_time)
print(res) # 1687848357.0
# 时间戳 ---------------------------------> 结构化时间
tp_time = time.time()
res = time.localtime(tp_time)

---

<!-- p.106 -->

7.4 ，了解
8, sys模块
8.1 打印进度条
print(res) # time.struct_time(tm_year=2023, tm_mon=6, tm_mday=27,
tm_hour=14, tm_min=48, tm_sec=36, tm_wday=1,tm_yday=178,
tm_isdst=0)
# 时间戳 --------------------------------> 世界标准时间 --------- 跟本地时间差8小
时
tp_time = time.time()
res = time.gmtime(tp_time)
print(res) # time.struct_time(tm_year=2023, tm_mon=6, tm_mday=27,
tm_hour=6, tm_min=50, tm_sec=35, tm_wday=1,tm_yday=178,
tm_isdst=0)
2, 结构化 <-------------------------> 格式化时间
## time.strptime('%Y-%m-%d %H:%M:%S %p',time.localtime())
res = time.strptime('1988-03-03 11:11:11','%Y-%m-%d %H:%M:%S')
print(res)
## time.struct_time(tm_year=1988, tm_mon=3, tm_mday=3, tm_hour=11, tm_min=11,
tm_sec=11, tm_wday=3, tm_yday=63, tm_isdst=-1)
'1988-03-03 11:11:11' + 7 -----------------------> 结构化时间
s_time = time.strptime('1988-03-03 11:11:11','%Y-%m-%d %H:%M:%S') # 结构化时间
miao = time.mktime(s_time) + 7 * 86400 ## 得到时间戳
struct_time = time.localtime(miao) ## 得到结构化时间
res = time.strftime('%Y-%m-%d %X',time.localtime(miao)) # 格式化时间
print(res) # 1988-03-10 11:11:11
import time
## linix 操作系统上常见
print(time.asctime()) # Tue Jun 27 15:26:23 2023
1 sys.argv # 命令行参数List，第一个元素是程序本身路径，用于获取终端里的参数
2 sys.exit(n) # 退出程序，正常退出时exit(0)
3 sys.version # 获取Python解释程序的版本信息
4 sys.maxint # 最大的Int值
5 sys.path # 返回模块的搜索路径，初始化时使用PYTHONPATH环境变量的值
6 sys.platform # 返回操作系统平台名称
import time
def process():
recv_size = 0
total_size = 333333
while recv_size < total_size:
# 下载了1024个字节数据
time.sleep(0.05)

---

<!-- p.107 -->

9，shutii 模块
recv_size += 1024
if recv_size > total_size:
recv_size = total_size
percent = recv_size / total_size
res = int(50 * percent) * "#"
# 打印进度条
print('\r[%-50s] %d%%' % (res,100 * percent) ,end='')
process()
## [##################################################] 100%
import shutill
# 将文件内容拷贝到另一个文件中
shutil.copyfileobj(open('old.xml','r'), open('new.xml', 'w'))
# 仅拷贝权限。内容、组、用户均不变
shutil.copymode('f1.log', 'f2.log') #目标文件必须存在
# 拷贝文件
shutil.copyfile('f1.log', 'f2.log') #目标文件无需存在
# 仅拷贝状态的信息，包括：mode bits, atime, mtime, flags
shutil.copystat('f1.log', 'f2.log') #目标文件必须存在
# 拷贝文件和权限
shutil.copy('f1.log', 'f2.log')
# 拷贝文件和状态信息
shutil.copy2('f1.log', 'f2.log')
# 递归的去拷贝文件夹
shutil.copytree('folder1', 'folder2', ignore=shutil.ignore_patterns('*.pyc',
'tmp*'))
# 目标目录不能存在，注意对folder2目录父级目录要有可写权限，ignore的意思是排除
shutil.copytree('f1', 'f2', symlinks=True,
ignore=shutil.ignore_patterns('*.pyc', 'tmp*'))
'''
通常的拷贝都把软连接拷贝成硬链接，即对待软连接来说，创建新的文件
'''
#递归的去删除文件
shutil.rmtree('folder1')
#递归的去移动文件，它类似mv命令，其实就是重命名。
shutil.move('folder1', 'folder3')
# 创建压缩包并返回文件路径，例如：zip、tar
# 创建压缩包并返回文件路径，例如：zip、tar

---

<!-- p.108 -->

10，pickle模块(有兼容性问题，了解就行)
base_name： 压缩包的文件名，也可以是压缩包的路径。只是文件名时，则保存至当前目录，否则保存至指
定路径，
# 如 data_bak =>保存至当前路径
# 如：/tmp/data_bak =>保存至/tmp/
format： 压缩包种类，“zip”, “tar”, “bztar”，“gztar”
root_dir： 要压缩的文件夹路径（默认当前目录）
owner： 用户，默认当前用户
group： 组，默认当前组
logger： 用于记录日志，通常是logging.Logger对象
#将 /data 下的文件打包放置当前程序目录
ret = shutil.make_archive("data_bak", 'gztar', root_dir='/data')
#将 /data下的文件打包放置 /tmp/目录
ret = shutil.make_archive("/tmp/data_bak", 'gztar', root_dir='/data')
#shutil 对压缩包的处理是调用 ZipFile 和 TarFile 两个模块来进行的，详细：
import zipfile
# 压缩
z = zipfile.ZipFile('laxi.zip', 'w')
z.write('a.log')
z.write('data.data')
z.close()
# 解压
z = zipfile.ZipFile('laxi.zip', 'r')
z.extractall(path='.')
z.close()
import tarfile
# 压缩
t=tarfile.open('/tmp/egon.tar','w')
t.add('/test1/a.py',arcname='a.bak')
t.add('/test1/b.py',arcname='b.bak')
t.close()
# 解压
t=tarfile.open('/tmp/egon.tar','r')
t.extractall('/egon')
t.close()
import pickle
res = pickle.dumps({1,2,3,4,5})
print(res)
#
b'\x80\x04\x95\x0f\x00\x00\x00\x00\x00\x00\x00\x8f\x94(K\x01K\x02K\x03K\x04K\x05
\x90.'
res = pickle.loads(res)
print(res)

---

<!-- p.109 -->

11，xml模块
# {1, 2, 3, 4, 5}
# coding:utf-8
import pickle
with open('a.pkl',mode='wb') as f:
# 一：在python3中执行的序列化操作如何兼容python2
# python2不支持protocol>2，默认python3中protocol=4
# 所以在python3中dump操作应该指定protocol=2
pickle.dump('你好啊',f,protocol=2)
with open('a.pkl', mode='rb') as f:
# 二：python2中反序列化才能正常使用
res=pickle.load(f)
print(res)
<?xml version="1.0"?>
<data>
<country name="Liechtenstein">
<rank updated="yes">2</rank>
<year>2008</year>
<gdppc>141100</gdppc>
<neighbor name="Austria" direction="E"/>
<neighbor name="Switzerland" direction="W"/>
</country>
<country name="Singapore">
<rank updated="yes">5</rank>
<year>2011</year>
<gdppc>59900</gdppc>
<neighbor name="Malaysia" direction="N"/>
</country>
<country name="Panama">
<rank updated="yes">69</rank>
<year>2011</year>
<gdppc>13600</gdppc>
<neighbor name="Costa Rica" direction="W"/>
<neighbor name="Colombia" direction="E"/>
</country>
</data>
xml协议在各个语言里的都 是支持的，在python中可以用以下模块操作xml：
# print(root.iter('year')) #全文搜索
# print(root.find('country')) #在root的子节点找，只找一个
# print(root.findall('country')) #在root的子节点找，找所有
import xml.etree.ElementTree as ET
tree = ET.parse("xmltest.xml")
root = tree.getroot()
print(root.tag)
#遍历xml文档
for child in root:

---

<!-- p.110 -->

print('========>',child.tag,child.attrib,child.attrib['name'])
for i in child:
print(i.tag,i.attrib,i.text)
#只遍历year 节点
for node in root.iter('year'):
print(node.tag,node.text)
#---------------------------------------
import xml.etree.ElementTree as ET
tree = ET.parse("xmltest.xml")
root = tree.getroot()
#修改
for node in root.iter('year'):
new_year=int(node.text)+1
node.text=str(new_year)
node.set('updated','yes')
node.set('version','1.0')
tree.write('test.xml')
#删除node
for country in root.findall('country'):
rank = int(country.find('rank').text)
if rank > 50:
root.remove(country)
tree.write('output.xml')
#在country内添加（append）节点year2
import xml.etree.ElementTree as ET
tree = ET.parse("a.xml")
root=tree.getroot()
for country in root.findall('country'):
for year in country.findall('year'):
if int(year.text) > 2000:
year2=ET.Element('year2')
year2.text='新年'
year2.attrib={'update':'yes'}
country.append(year2) #往country节点下添加子节点
tree.write('a.xml.swap')
自己创建xml文档：
import xml.etree.ElementTree as ET
new_xml = ET.Element("namelist")
name = ET.SubElement(new_xml,"name",attrib={"enrolled":"yes"})
age = ET.SubElement(name,"age",attrib={"checked":"no"})
sex = ET.SubElement(name,"sex")
sex.text = '33'
name2 = ET.SubElement(new_xml,"name",attrib={"enrolled":"no"})
age = ET.SubElement(name2,"age")
age.text = '19'

---

<!-- p.111 -->

12，configparser模块（导入某种格式的配置文件）
12.1 读取
et = ET.ElementTree(new_xml) #生成文档对象
et.write("test.xml", encoding="utf-8",xml_declaration=True)
ET.dump(new_xml) #打印生成的格式
## 配置文件内容
[section1]
k1 = v1
k2:v2
user=egon
age=18
is_admin=true
salary=31
[section2]
k1 = v1
import configparser
config=configparser.ConfigParser()
config.read('a.cfg') # 读取配置文件
#查看所有的标题
res=config.sections() #['section1', 'section2']
print(res)
#查看标题section1下所有key=value的key
options=config.options('section1')
print(options) #['k1', 'k2', 'user', 'age', 'is_admin', 'salary']
#查看标题section1下所有key=value的(key,value)格式
item_list=config.items('section1')
print(item_list)
#[('k1', 'v1'), ('k2', 'v2'), ('user', 'egon'), ('age', '18'), ('is_admin',
'true'), ('salary', '31')]
#查看标题section1下user的值=>字符串格式
val=config.get('section1','user')
print(val) #egon
#查看标题section1下age的值=>整数格式
val1=config.getint('section1','age')
print(val1) #18
#查看标题section1下is_admin的值=>布尔值格式
val2=config.getboolean('section1','is_admin')
print(val2) #True

---

<!-- p.112 -->

12.2 改写
13 hashlib 模块
14 subprocess模块
#查看标题section1下salary的值=>浮点型格式
val3=config.getfloat('section1','salary')
print(val3) #31.0
import configparser
config=configparser.ConfigParser()
config.read('a.cfg',encoding='utf-8')
#删除整个标题section2
config.remove_section('section2')
#删除标题section1下的某个k1和k2
config.remove_option('section1','k1')
config.remove_option('section1','k2')
#判断是否存在某个标题
print(config.has_section('section1'))
#判断标题section1下是否有user
print(config.has_option('section1',''))
#添加一个标题
config.add_section('egon')
#在标题egon下添加name=egon,age=18的配置
config.set('egon','name','egon')
config.set('egon','age',18) #报错,必须是字符串
#最后将修改的内容写入文件,完成最终的修改
config.write(open('a.cfg','w'))
# hash是一类算法，该算法根据传入的内容，经过运算得到一串哈希值
# hash值的特单
1，传入的内容一样，则得到的结果一样
2，无论传多大内容，得到的hash值长度一样
3，不能反向破解
import subprocess
'''
sh-3.2# ls /Users/egon/Desktop |grep txt$
mysql.txt

---

<!-- p.113 -->

15，日志模块（logging）
14.1 日志级别
tt.txt
事物.txt
'''
## 查看 /Users/jieli/Desktop 下的文件列表
res1=subprocess.Popen('ls
/Users/jieli/Desktop',shell=True,stdout=subprocess.PIPE，stderr=subprocess.PIPE)
# shell = True 意思是调一个终端 stdout 是正确结果的输出管道 stderr 是接受错误结果的输出
管道
# res1 是对象
print(res2.stdout.read()) # 打印正确的结果，得到的格式是字节，解码用的是系统的编码格式,mac
为utf-8
print(res1.stderr.read()) # 打印错误的结果，得到的是字节格式，解码用的是系统的编码格式，
windows为gbk
res=subprocess.Popen('grep
txt$',shell=True,stdin=res1.stdout,stdout=subprocess.PIPE)
print(res.stdout.read().decode('utf-8'))
#等同于上面,但是上面的优势在于,一个数据流可以和另外一个数据流交互,可以通过爬虫得到结果然后交给
grep
res1=subprocess.Popen('ls /Users/jieli/Desktop |grep
txt$',shell=True,stdout=subprocess.PIPE)
print(res1.stdout.read().decode('utf-8'))
#windows下:
# dir | findstr 'test*'
# dir | findstr 'txt$'
import subprocess
res1=subprocess.Popen(r'dir C:\Users\Administrator\PycharmProjects\test\函数备
课',shell=True,stdout=subprocess.PIPE)
res=subprocess.Popen('findstr test*',shell=True,stdin=res1.stdout,
stdout=subprocess.PIPE)
print(res.stdout.read().decode('gbk')) #subprocess使用当前系统默认编码，得到结果为
bytes类型，在windows下需要用gbk解码
import logging
CRITICAL = 50 #FATAL = CRITICAL
ERROR = 40
WARNING = 30 #WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0 #不设置

---

<!-- p.114 -->

14.2 默认级别为warning，默认打印到终端
14.3 为logging模块指定全局配置，针对所有logger有效，控制打印
到文件中
import logging
logging.debug('调试debug')
logging.info('消息info')
logging.warning('警告warn') ## WARNING:root:警告warn
logging.error('错误error') ## ERROR:root:错误error
logging.critical('严重critical') ## CRITICAL:root:严重critical
'''
WARNING:root:警告warn
ERROR:root:错误error
CRITICAL:root:严重critical
'''
'''
可在logging.basicConfig()函数中可通过具体参数来更改logging模块默认行为，可用参数有
filename：用指定的文件名创建FiledHandler（后边会具体讲解handler的概念），这样日志会被存
储在指定的文件中。
filemode：文件打开方式，在指定了filename时使用这个参数，默认值为“a”还可指定为“w”。
format：指定handler使用的日志显示格式。
datefmt：指定日期时间格式。
level：设置rootlogger（后边会讲解具体概念）的日志级别
stream：用指定的stream创建StreamHandler。可以指定输出到sys.stderr,sys.stdout或者文
件，默认为sys.stderr。若同时列出了 filename和stream两个参数，则stream参数会被忽
略。
'''
## 例如：
logging.basicConfig(
format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s' # 就这样自定义
格式
)
format参数中可能用到的格式化串：
%(name)s # Logger的名字
%(levelno)s # 数字形式的日志级别
%(levelname)s # 文本形式的日志级别
%(pathname)s # 调用日志输出函数的模块的完整路径名，可能没有
%(filename)s # 调用日志输出函数的模块的文件名
%(module)s # 调用日志输出函数的模块名
%(funcName)s # 调用日志输出函数的函数名
%(lineno)d # 调用日志输出函数的语句所在的代码行
%(created)f # 当前时间，用UNIX标准的表示时间的浮 点数表示
%(relativeCreated)d # 输出日志信息时的，自Logger创建以 来的毫秒数
%(asctime)s # 字符串形式的当前时间。默认格式是 “2003-07-08 16:49:45,896”。逗号后面的是毫
秒
%(thread)d # 线程ID。可能没有
%(threadName)s # 线程名。可能没有
%(process)d # 进程ID。可能没有
%(message)s # 用户输出的消息

---

<!-- p.115 -->

14.4 使用例子
14.5 logging模块的Formatter，Handler，Logger，Filter对象
#========使用
import logging
logging.basicConfig(
## 写到文件里的编码格式以系统编码格式为准，Windows为gbk
filename='access.log', ## 日志输出的位置
format='%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s',
## 一个日志输出的格式
datefmt='%Y-%m-%d %H:%M:%S %p', ## 输出里的时间格式
level=10 ## 日志错误级别
)
logging.debug('调试debug')
logging.info('消息info')
logging.warning('警告warn')
logging.error('错误error')
logging.critical('严重critical')
#========结果
access.log内容:
2017-07-28 20:32:17 PM - root - DEBUG -test: 调试debug
2017-07-28 20:32:17 PM - root - INFO -test: 消息info
2017-07-28 20:32:17 PM - root - WARNING -test: 警告warn
2017-07-28 20:32:17 PM - root - ERROR -test: 错误error
2017-07-28 20:32:17 PM - root - CRITICAL -test: 严重critical
#logger：产生日志的对象
#Filter：过滤日志的对象
#Handler：接收日志然后控制打印到不同的地方，FileHandler用来打印到文件中，StreamHandler用来
打印到终端
#Formatter对象：可以定制不同的日志格式对象，然后绑定给不同的Handler对象使用，以此来控制不同的
Handler的日志格式
'''
critical=50
error =40
warning =30
info = 20
debug =10
'''
import logging
#1、logger对象：负责产生日志，然后交给Filter过滤，然后交给不同的Handler输出
logger=logging.getLogger(__file__)
#2、Filter对象：不常用，略
#3、Handler对象：接收logger传来的日志，然后控制输出
h1=logging.FileHandler('t1.log') #打印到文件
h2=logging.FileHandler('t2.log') #打印到文件

---

<!-- p.116 -->

14.6 Logger与Handler的级别
h3=logging.StreamHandler() #打印到终端
#4、Formatter对象：日志格式
formmater1=logging.Formatter(
'%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s',
datefmt='%Y-%m-%d %H:%M:%S %p',
)
formmater2=logging.Formatter(
'%(asctime)s : %(message)s',
datefmt='%Y-%m-%d %H:%M:%S %p',
)
formmater3=logging.Formatter('%(name)s %(message)s',)
#5、为Handler对象绑定格式
h1.setFormatter(formmater1)
h2.setFormatter(formmater2)
h3.setFormatter(formmater3)
#6、将Handler添加给logger并设置日志级别
logger.addHandler(h1)
logger.addHandler(h2)
logger.addHandler(h3)
logger.setLevel(10)
#7、测试
logger.debug('debug')
logger.info('info')
logger.warning('warning')
logger.error('error')
logger.critical('critical')
### logger是第一级过滤，然后才能到handler，我们可以给logger和handler同时设置level
#验证
import logging
form=logging.Formatter(
'%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s',
datefmt='%Y-%m-%d %H:%M:%S %p',
)
ch=logging.StreamHandler()
ch.setFormatter(form)
# ch.setLevel(10)
ch.setLevel(20)
l1=logging.getLogger('root')
# l1.setLevel(20)
l1.setLevel(10)
l1.addHandler(ch)

---

<!-- p.117 -->

14.7 Logger的继承（了解）
14.8 应用
14.8.1 logging配置
l1.debug('l1 debug')
import logging
formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s -%(module)s:
%(message)s',
datefmt='%Y-%m-%d %H:%M:%S %p',)
ch=logging.StreamHandler()
ch.setFormatter(formatter)
logger1=logging.getLogger('root')
logger2=logging.getLogger('root.child1')
logger3=logging.getLogger('root.child1.child2')
logger1.addHandler(ch)
logger2.addHandler(ch)
logger3.addHandler(ch)
logger1.setLevel(10)
logger2.setLevel(10)
logger3.setLevel(10)
logger1.debug('log1 debug')
logger2.debug('log2 debug')
logger3.debug('log3 debug')
'''
2017-07-28 22:22:05 PM - root - DEBUG -test: log1 debug
2017-07-28 22:22:05 PM - root.child1 - DEBUG -test: log2 debug
2017-07-28 22:22:05 PM - root.child1 - DEBUG -test: log2 debug
2017-07-28 22:22:05 PM - root.child1.child2 - DEBUG -test: log3 debug
2017-07-28 22:22:05 PM - root.child1.child2 - DEBUG -test: log3 debug
2017-07-28 22:22:05 PM - root.child1.child2 - DEBUG -test: log3 debug
'''
"""
logging配置
"""
import os
import logging.config
# 定义三种日志输出格式 开始
standard_format = '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%
(filename)s:%(lineno)d]' \
'[%(levelname)s][%(message)s]' #其中name为getlogger指定的名字

---

<!-- p.118 -->

simple_format = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%
(message)s'
id_simple_format = '[%(levelname)s][%(asctime)s] %(message)s'
# 定义日志输出格式 结束
logfile_dir = os.path.dirname(os.path.abspath(__file__)) # log文件的目录
logfile_name = 'all2.log' # log文件名
# 如果不存在定义的日志目录就创建一个
if not os.path.isdir(logfile_dir):
os.mkdir(logfile_dir)
# log文件的全路径
logfile_path = os.path.join(logfile_dir, logfile_name)
# log配置字典
LOGGING_DIC = {
'version': 1,
'disable_existing_loggers': False,
'formatters': {
'standard': {
'format': standard_format
},
'simple': {
'format': simple_format
},
},
'filters': {},
'handlers': {
#打印到终端的日志
'console': {
'level': 'DEBUG',
'class': 'logging.StreamHandler', # 打印到屏幕
'formatter': 'simple'
},
#打印到文件的日志,收集info及以上的日志
'default': {
'level': 'DEBUG',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件
'formatter': 'standard',
'filename': logfile_path, # 日志文件
'maxBytes': 1024*1024*5, # 日志大小 5M
'backupCount': 5,
'encoding': 'utf-8', # 日志文件的编码，再也不用担心中文log乱码了
},
},
'loggers': {
#logging.getLogger(__name__)拿到的logger配置
'': {
'handlers': ['default', 'console'], # 这里把上面定义的两个handler都加
上，即log数据既写入文件又打印到屏幕
'level': 'DEBUG',
'propagate': True, # 向上（更高level的logger）传递
},
},

---

<!-- p.119 -->

14.8.2 使用
14.8.3 注意注意注意
}
def load_my_logging_cfg():
logging.config.dictConfig(LOGGING_DIC) # 导入上面定义的logging配置
logger = logging.getLogger(__name__) # 生成一个log实例
logger.info('It works!') # 记录该文件的运行状态
if __name__ == '__main__':
load_my_logging_cfg()
"""
MyLogging Test
"""
import time
import logging
import my_logging # 导入自定义的logging配置
logger = logging.getLogger(__name__) # 生成logger实例
def demo():
logger.debug("start range... time:{}".format(time.time()))
logger.info("中文测试开始。。。")
for i in range(10):
logger.debug("i:{}".format(i))
time.sleep(0.2)
else:
logger.debug("over range... time:{}".format(time.time()))
logger.info("中文测试结束。。。")
if __name__ == "__main__":
my_logging.load_my_logging_cfg() # 在你程序文件的入口加载自定义logging配置
demo()
"""
MyLogging Test
"""
import time
import logging
import my_logging # 导入自定义的logging配置
logger = logging.getLogger(__name__) # 生成logger实例
def demo():
logger.debug("start range... time:{}".format(time.time()))
logger.info("中文测试开始。。。")
for i in range(10):
logger.debug("i:{}".format(i))

---

<!-- p.120 -->

14.8.4 另外一个django的配置，瞄一眼就可以，跟上面的一样
time.sleep(0.2)
else:
logger.debug("over range... time:{}".format(time.time()))
logger.info("中文测试结束。。。")
if __name__ == "__main__":
my_logging.load_my_logging_cfg() # 在你程序文件的入口加载自定义logging配置
demo()
#logging_config.py
LOGGING = {
'version': 1,
'disable_existing_loggers': False,
'formatters': {
'standard': {
'format': '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%
(name)s][%(filename)s:%(lineno)d]'
'[%(levelname)s][%(message)s]'
},
'simple': {
'format': '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%
(message)s'
},
'collect': {
'format': '%(message)s'
}
},
'filters': {
'require_debug_true': {
'()': 'django.utils.log.RequireDebugTrue',
},
},
'handlers': {
#打印到终端的日志
'console': {
'level': 'DEBUG',
'filters': ['require_debug_true'],
'class': 'logging.StreamHandler',
'formatter': 'simple'
},
#打印到文件的日志,收集info及以上的日志
'default': {
'level': 'INFO',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件，自动切
'filename': os.path.join(BASE_LOG_DIR, "xxx_info.log"), # 日志文件
'maxBytes': 1024 * 1024 * 5, # 日志大小 5M
'backupCount': 3,
'formatter': 'standard',
'encoding': 'utf-8',
},
#打印到文件的日志:收集错误及以上的日志
'error': {
'level': 'ERROR',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件，自动切
'filename': os.path.join(BASE_LOG_DIR, "xxx_err.log"), # 日志文件

---

<!-- p.121 -->

14.9 直奔主题，常规使用
14.9.1 日志级别与配置
'maxBytes': 1024 * 1024 * 5, # 日志大小 5M
'backupCount': 5,
'formatter': 'standard',
'encoding': 'utf-8',
},
#打印到文件的日志
'collect': {
'level': 'INFO',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件，自动切
'filename': os.path.join(BASE_LOG_DIR, "xxx_collect.log"),
'maxBytes': 1024 * 1024 * 5, # 日志大小 5M
'backupCount': 5,
'formatter': 'collect',
'encoding': "utf-8"
}
},
'loggers': {
#logging.getLogger(__name__)拿到的logger配置
'': {
'handlers': ['default', 'console', 'error'],
'level': 'DEBUG',
'propagate': True,
},
#logging.getLogger('collect')拿到的logger配置
'collect': {
'handlers': ['console', 'collect'],
'level': 'INFO',
}
},
}
# -----------
# 用法:拿到俩个logger
logger = logging.getLogger(__name__) #线上正常的日志
collect_logger = logging.getLogger("collect") #领导说,需要为领导们单独定制领导们看的日
志
import logging
# 在
# 一：日志配置
logging.basicConfig(
# 1、日志输出位置：1、终端 2、文件
# filename='access.log', # 不指定，默认打印到终端
# 2、日志格式
format='%(asctime)s - %(name)s - %(levelname)s -%(module)s: %(message)s',
# 3、时间格式
datefmt='%Y-%m-%d %H:%M:%S %p',
# 4、日志级别

---

<!-- p.122 -->

14.9.2 日志配置字典（setting.py）
# critical => 50
# error => 40
# warning => 30
# info => 20
# debug => 10
level=30,
)
# 二：输出日志
logging.debug('调试debug')
logging.info('消息info')
logging.warning('警告warn')
logging.error('错误error')
logging.critical('严重critical')
'''
# 注意下面的root是默认的日志名字
WARNING:root:警告warn
ERROR:root:错误error
CRITICAL:root:严重critical
'''
"""
logging配置
在 setting.py中定义
"""
import os
# 1、定义三种日志输出格式，日志中可能用到的格式化串如下
# %(name)s Logger的名字
# %(levelno)s 数字形式的日志级别
# %(levelname)s 文本形式的日志级别
# %(pathname)s 调用日志输出函数的模块的完整路径名，可能没有
# %(filename)s 调用日志输出函数的模块的文件名
# %(module)s 调用日志输出函数的模块名
# %(funcName)s 调用日志输出函数的函数名
# %(lineno)d 调用日志输出函数的语句所在的代码行
# %(created)f 当前时间，用UNIX标准的表示时间的浮 点数表示
# %(relativeCreated)d 输出日志信息时的，自Logger创建以 来的毫秒数
# %(asctime)s 字符串形式的当前时间。默认格式是 “2003-07-08 16:49:45,896”。逗号后面的是毫
秒
# %(thread)d 线程ID。可能没有
# %(threadName)s 线程名。可能没有
# %(process)d 进程ID。可能没有
# %(message)s用户输出的消息
# 2、强调：其中的%(name)s为getlogger时指定的名字
## 这些是预先定义好的自定义格式
standard_format = '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%
(filename)s:%(lineno)d]' \
'[%(levelname)s][%(message)s]'
simple_format = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%
(message)s'

---

<!-- p.123 -->

test_format = '%(asctime)s] %(message)s'
# 3、日志配置字典
LOGGING_DIC = {
'version': 1,
'disable_existing_loggers': False,
'formatters': {
# 自己自定义的日志格式，可以自己改
'standard': {
# 自己定义的自定义格式
'format': standard_format
},
'simple': {
'format': simple_format
},
'test': {
'format': test_format
},
},
'filters': {},
## 日志的接受者，不同的handle可以使日志输出到不同位置
'handlers': {
#打印到终端的日志
'console': {
'level': 'DEBUG',
'class': 'logging.StreamHandler', # 打印到屏幕
## 指定输出格式
'formatter': 'simple'
},
#打印到文件的日志,收集info及以上的日志
'default': {
'level': 'DEBUG',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件,日志轮转
'formatter': 'standard',
# 可以定制日志文件路径
# BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # log文件的目
录
# LOG_PATH = os.path.join(BASE_DIR,'a1.log')
'filename': 'a1.log', # 日志文件
'maxBytes': 1024*1024*5, # 日志大小 5M
'backupCount': 5,
'encoding': 'utf-8', # 日志文件的编码，再也不用担心中文log乱码了
},
## 测试用的日志格式
'other': {
'level': 'DEBUG',
'class': 'logging.FileHandler', # 保存到文件
'formatter': 'test',
'filename': 'a2.log',##拿到项目的跟文件夹
os.path.dirname(os.path.dirname(__file__))
'encoding': 'utf-8',
},

---

<!-- p.124 -->

14.9.3 使用
},
# 负责产生日志，产生的日志传递给handler负责处理
'loggers': {
#logging.getLogger(__name__)拿到的logger配置
'kkk': {
# kkk 产生的日志传给谁
'handlers': ['default', 'console'], # 这里把上面定义的两个handler都加
上，即log数据既写入文件又打印到屏幕
'level': 'DEBUG', # loggers(第一层日志级别关限制)--->handlers(第二层日志级
别关卡限制)
'propagate': False, # 默认为True，向上（更高level的logger）传递，通常设置
为False即可，否则会一份日志向上层层# 传递
},
'bbb': {
# kkk 产生的日志传给谁
'handlers': ['console'], # 这里把上面定义的两个handler都加上，即log数据既
写入文件又打印到屏幕
'level': 'DEBUG', # loggers(第一层日志级别关限制)--->handlers(第二层日志级
别关卡限制)
'propagate': False, # 默认为True，向上（更高level的logger）传递，通常设置
为False即可，否则会一份日志向上层层# 传递
},
'专门的采集': {
'handlers': ['other',],
'level': 'DEBUG',
'propagate': False,
},
},
}
import settings
# !!!强调!!!
# 1、logging是一个包，需要使用其下的config、getLogger，可以如下导入
# 可能不能正常使用
# import logging.config
# import logging.getLogger
# 2、也可以使用如下导入
# from logging import config,getLogger
from logging import config # 这样连同logging.getLogger都一起导入了,然后使用前缀
logging.config.
from logging import getLogger # 用于获取配置文件里的日志生产者
# 3、加载配置
# 把配置好的配置字典扔进去
logging.config.dictConfig(settings.LOGGING_DIC)
logger1 = getLogger("kkk") ## kkk 是可以同时向终端和文件里输出日志的
logger2 = getLogger('bbb') ### bbb 只向终端里输出日志
# 4、输出日志

---

<!-- p.125 -->

14.9.4 日志轮换
15，struct模块
三，常用API速查
logger1=logging.getLogger('用户交易')
logger1.info('egon儿子alex转账3亿冥币')
# logger2=logging.getLogger('专门的采集') # 名字传入的必须是'专门的采集'，与LOGGING_DIC
中的配置唯一对应
# logger2.debug('专门采集的日志')
## 'class': 'logging.handlers.RotatingFileHandler', # 保存到文件,日志轮转
## 'maxBytes': 1024*1024*5, # 日志大小 5M
## 'backupCount': 5, 最多保运几份
#打印到文件的日志,收集info及以上的日志
'default': {
'level': 'DEBUG',
'class': 'logging.handlers.RotatingFileHandler', # 保存到文件,日志轮转
'formatter': 'standard',
# 可以定制日志文件路径
# BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # log文件的目
录
# LOG_PATH = os.path.join(BASE_DIR,'a1.log')
'filename': 'a1.log', # 日志文件
'maxBytes': 1024*1024*5, # 日志大小 5M
'backupCount': 5,
'encoding': 'utf-8', # 日志文件的编码，再也不用担心中文log乱码了
},
## 该模块可以把一个类型，如数字，转成固定长度的bytes
import struct
bytes = struct.pack('i',1000) ## 拿到长度固定的四个字节
num = struct.unpack('i',bytes)[0] ## 结果是元祖，元祖里拿到数字拿到数字

---

<!-- p.126 -->

1，字符串
1.1 字符串查找方法
2.2 去除首位信息
3.3 大小写转换
4.4 格式排版：
5.5 数字格式化
startswith() #以指定字符串开头；
Endswith() # 以指定字符串结尾；
find() # 返回字符串第一次出现的位置；
Rfind() # 返回最后一次出现的位置；
Count() # 返回某个字符总共出现的次数；
Isallnum() # 判断所有字符是不是全是数字或者字母；
Strip() # 去除字符串首位指定信息； 默认去除首位空格
Lstrip() # 去除左边的指定信息；
Rtrip() # 去除右边的指定信息；
Capitalize() # 产生新的字符串，首字母大写；
Title() # 每个单词首字母大写；
Upper() # 所有字母转换成大写；
Lower() # 所有字母转换成小写；
Swapcase() # 所有字母大小写转换；
# 1. Center() ljust() rjust() 用于实现排版；
# 默认用空格填充
# 2. 接受两个参数，第一个参数是要实现的长度，第二个字符是要填充的字符
s = "aini"
s.center(10,"*") # 用*左右填充让s达到10的长度
# 格式化
"我是{0},我喜欢数字{1:*^8}".format("艾尼","666")
# ：后面是依次是 填充的字符 对齐方式(<^> 左中右) 格式化长度
# 如：1:*^20 用*号居中对齐，长度为 20 个字符
# 数字格式化

---

<!-- p.127 -->

数字 格式 输出 描述
3.1415926 { :.2f } 3.14 保留小数点后两位
3.1415926 { :+.2f } 3.14 带符号的保留小数点后两位
2.71828 { :.0f } 3 不带小数
5 { :0>2d } 5 数字补零（填充左边，宽度为2)
5 { :x<4d } 5xxx 数字补x（填充右边，宽度为4)
10 { :x<4d } 10xx 数字补x（填充右边，宽度为4)
1000000 { :, } 1，000，000 以逗号分割的数字形式
0.25 { :.2% } 25.00% 百分比格式
方法 要点 描述
list.append(x) 增加元素 将元素x增加到列表list尾部
list.extend(aList) 增加元素 将列表aList素有元素加到列表list尾部
list.insert(index,x) 增加元素 将列表list指定index处插入元素x
list.remove(x) 删除元素 删除列表中首次出现的指定元素x
list.pop(index) 删除元素
删除index处的元素并返回，默认删除最后一个元素并返
回
list.clear()
删除所有元
素
删除原数，不会删除列表对象
list.index(x) 访问元素 返回第一个x的索引，若不存在则抛出异常
list.count(x) 计数 返回元素x在列表中出现的次数
len(list)
返回列表长
度
返回类表中总元素的个数
6.6 其他方法：
2，列表
Isalnum() # 是否全为数字或字母；
Isalpha() # 是不是都是字母或汉字组成；
Isdigit() # 是不是都是由数字组成；
Isspace() # 检测是否为空白字符；
Isupper() # 检测是否为大写字母；
Islower() # 检测是否为小写字母；

---

<!-- p.128 -->

方法 要点 描述
list.reverse() 翻转列表 所有元素原地翻转
list.sort() 排序 所有元素原地排序
list.copy() 浅拷贝 返回列表对象的浅拷贝
3，字典
4，Python常用内置函数
4.1 round() 函数
round()是一个处理数值的内置函数，它返回浮点数x的四舍五入值
4.2 all() 和 any()
all()和any()，用于判断可迭代对象中的元素是否为True。它们返回布尔值True或False
4.3 lambda函数
# update(),把第二个字典加到第一个字典里面
a.update(b) # 把字典b加到a里面
# 可以用 del 删除键值对
# Del a[‘name’] del a[‘sex’]
# 可以用 clear()方法删除所有键值对；
# Pop()方法可以删除键值对，并将值返回
a.pop("name")
# Popitem()方法:随机删除键值对，并将其返回
# 序列解包
a.values()
a.items()
numbers = [1, 2, 3, 4, 5]
if all(num > 0 for num in numbers):
print("All numbers are positive")
else:
print("There are some non-positive numbers")
if any(num > 4 for num in numbers):
print("At least one number is greater than 4")
else:
print("No number is greater than 4")

---

<!-- p.129 -->

4.4 sorted()函数
sorted()是一个内置函数，它用于对可迭代对象进行排序。
sorted()函数接受一个可迭代对象作为参数，并返回一个新的已排序的列表。
4.5 map()函数
lambda x: x + 5
这个Lambda函数可以像下面这样使用：
add_five = lambda x: x + 5
result = add_five(10)
print(result) # 输出 15
sorted(iterable, key=None, reverse=False)
# iterable: 需要排序的可迭代对象，例如列表、元组、集合、字典等。
#key（可选参数）: 用于指定排序的关键字。key是一个函数，它将作用于iterable中的每个元素，并返回
一个用于排序的关键字。默认为None，表示按照元素的大小进行排序。
# reverse（可选参数）: 用于指定排序的顺序。如果设置为True，则按照逆序排序。默认为False，表示
按照正序排序。
numbers = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
sorted_numbers = sorted(numbers)
print(sorted_numbers) # 输出结果为 [1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9]
words = ["apple", "banana", "cherry", "date"]
sorted_words = sorted(words, key=len)
print(sorted_words) # 输出结果为 ["date", "apple", "banana", "cherry"]
numbers = [(1, 2), (3, 4), (2, 1), (4, 3)]
sorted_numbers = sorted(numbers, key=lambda x: x[1])
print(sorted_numbers) # 输出结果为 [(2, 1), (1, 2), (4, 3), (3, 4)]
# 在上面的示例中，第一个示例对一个整数列表进行排序，第二个示例对一个字符串列表按照字符串长度进行
排序，第三个示例对一个元组列表按照元组中第二个元素进行排序，其中使用了lambda表达式作为key参数来
指定排序方式。
map(函数名，可迭代对象)
map函数是一种高阶函数，它接受一个函数和一个可迭代对象作为参数，返回一个新的可迭代对象，
map得到的是一个迭代器
# 其中每个元素都是将原可迭代对象中的元素应用给定函数后的结果。
# 可以简单理解为对可迭代对象中的每个元素都执行同一个操作，返回一个新的结果集合。
# 需要注意的是，map函数返回的是一个迭代器对象，因此如果要使用它的结果，需要将它转换为一个列表
list()、元组tuple()或集合set()和其他可迭代对象。
map函数的一些应用
1.用来批量接收变量
n,m = map(int,input().split())
2.对可迭代对象进行批量处理返回列表map
m = map("".join,[["a","b","c"],["d","e","f"]])
print(m) -> ["abc","def"]

---

<!-- p.130 -->

4.5 filter()函数
filter() 函数是 Python 内置函数之一，它用于过滤序列中的元素，返回一个满足条件的新序列。
filter() 函数的语法如下：
4.6 ASCII码的函数
4.7 转进制函数
4.8 列表
3.配合lambda函数达到自己想要的效果
numbers = [1, 2, 3, 4, 5]
doubled_numbers = map(lambda x: x * 2, numbers)
print(list(doubled_numbers)) -> [2, 4, 6, 8, 10]
my_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = filter(lambda x: x % 2 == 0, my_list)
print(list(result)) # 输出 [2, 4, 6, 8, 10]
在这个例子中，lambda x: x % 2 == 0 是一个 lambda 函数，用于判断一个数是否为偶数。filter()
函数将这个 lambda 函数作为参数，对列表 my_list 进行过滤，最后返回一个新列表，其中包含
my_list 中所有的偶数。
ord() # 接收字符转换ASCII码
chr() # 接收ASCII码转换字符
# 其它进制通用转10进制
int("x",y) # x是你要转的数，而y是这个数是由什么进制表示的，
# 当y为0时就按x的前缀来看如 0bx 二进制,0b 0o 0x,分别是二，八，十六
# 10进制转其他进制
hex() # 转16
oct() # 转8
# 有一个函数很适合10进制转其他各种进制
divmod(x,y)
#其作用是同时返回两个数的商和余数。
# 所以要这样接收它的值 a,b = divmod(x,y)
Python中的list是一个非常重要的数据类型，可以用来存储多个值，包括数字、字符串、对象等等。
以下是一些常见的list函数及其示例：
append() - 将一个元素添加到list的末尾
fruits = ['apple', 'banana', 'cherry']
fruits.append('orange')
print(fruits) # ['apple', 'banana', 'cherry', 'orange']
extend() - 将一个list的所有元素添加到另一个list的末尾
fruits = ['apple', 'banana', 'cherry']
more_fruits = ['orange', 'mango', 'grape']

---

<!-- p.131 -->

fruits.extend(more_fruits)
print(fruits) # ['apple', 'banana', 'cherry', 'orange', 'mango', 'grape']
insert() - 在指定的位置插入一个元素
fruits = ['apple', 'banana', 'cherry']
fruits.insert(1, 'orange')
print(fruits) # ['apple', 'orange', 'banana', 'cherry']
remove() - 删除指定的元素
fruits = ['apple', 'banana', 'cherry']
fruits.remove('banana')
print(fruits) # ['apple', 'cherry']
pop() - 删除指定位置的元素（默认为最后一个元素），并返回该元素的值
fruits = ['apple', 'banana', 'cherry']
last_fruit = fruits.pop()
print(last_fruit) # 'cherry'
print(fruits) # ['apple', 'banana']
index() - 返回指定元素在list中的索引位置
fruits = ['apple', 'banana', 'cherry']
banana_index = fruits.index('banana')
print(banana_index) # 1
count() - 返回指定元素在list中出现的次数
fruits = ['apple', 'banana', 'cherry', 'banana', 'banana']
banana_count = fruits.count('banana')
print(banana_count) # 3
sort() - 将list中的元素进行排序
fruits = ['apple', 'banana', 'cherry']
fruits.sort()
print(fruits) # ['apple', 'banana', 'cherry']
reverse() - 将list中的元素翻转
fruits = ['apple', 'banana', 'cherry']
fruits.reverse()
print(fruits) # ['cherry', 'banana', 'apple']
len() - 返回list中元素的数量
fruits = ['apple', 'banana', 'cherry']
num_fruits = len(fruits)
print(num_fruits) # 3
copy() - 返回一个list的副本
fruits = ['apple', 'banana', 'cherry']
fruits_copy = fruits.copy()
print(fruits_copy) # ['apple', 'banana', 'cherry']
clear() - 删除list中的所有元素
fruits = ['apple', 'banana', 'cherry']
fruits.clear()
print(fruits) # []
max() - 返回list中最大的元素
numbers = [5, 10, 3, 8, 15]
max_num = max(numbers)
print(max_num) # 15

---

<!-- p.132 -->

min() - 返回list中最小的元素
numbers = [5, 10, 3, 8, 15]
min_num = min(numbers)
print(min_num) # 3
sum() - 返回list中所有元素的和（仅适用于数字类型的list）
numbers = [5, 10, 3, 8, 15]
sum_nums = sum(numbers)
print(sum_nums) # 41
any() - 如果list中至少有一个元素为True，则返回True
bool_list = [False, True, False]
has_true = any(bool_list)
print(has_true) # True
all() - 如果list中的所有元素都为True，则返回True
bool_list = [True, True, True]
all_true = all(bool_list)
print(all_true) # True
enumerate() - 返回一个枚举对象，其中包含list中每个元素的索引和值
fruits = ['apple', 'banana', 'cherry']
for index, fruit in enumerate(fruits):
print(index, fruit)
# 0 apple
# 1 banana
# 2 cherry
map() - 对list中的每个元素应用函数，并返回结果的list
numbers = [1, 2, 3, 4]
squares = list(map(lambda x: x ** 2, numbers))
print(squares) # [1, 4, 9, 16]
filter() - 返回list中符合条件的元素的子集
numbers = [1, 2, 3, 4, 5, 6]
even_nums = list(filter(lambda x: x % 2 == 0, numbers))
print(even_nums) # [2, 4, 6]
reduce() - 对list中的元素应用函数，将其归约为单个值
from functools import reduce
numbers = [1, 2, 3, 4]
sum_nums = reduce(lambda x, y: x + y, numbers)
print(sum_nums) # 10
zip() - 将多个list的元素配对，返回一个元组的list
fruits = ['apple', 'banana', 'cherry']
colors = ['red', 'yellow', 'red']
fruit_colors = list(zip(fruits, colors))
print(fruit_colors) # [('apple', 'red'), ('banana', 'yellow'), ('cherry',
'red')]
sorted() - 返回一个新的已排序的list
numbers = [3, 2, 1, 5, 4]
sorted_nums = sorted(numbers)
print(sorted_nums) # [1, 2, 3, 4, 5]

---

<!-- p.133 -->

4.9 元祖
join() - 将list中的字符串连接成一个字符串
fruits = ['apple', 'banana', 'cherry']
fruit_string = ', '.join(fruits)
print(fruit_string) # 'apple, banana, cherry'
slice() - 返回一个list的子集，根据索引的起始和结束位置
fruits = ['apple', 'banana', 'cherry', 'orange', 'grape']
subset = fruits[1:4]
print(subset) # ['banana', 'cherry', 'orange']
希望这些函数能够帮助你更好地使用Python的list类型。
Python元组是不可变序列，它不支持在原地修改元素。因此，Python元组的函数相对较少。
以下是Python元组的所有函数：
count
count方法返回元组中指定元素的数量。
my_tuple = ('apple', 'banana', 'apple', 'orange', 'banana', 'apple')
count = my_tuple.count('apple')
print(count) # 输出：3
index
index方法返回元组中指定元素第一次出现的索引。
my_tuple = ('apple', 'banana', 'apple', 'orange', 'banana', 'apple')
index = my_tuple.index('orange')
print(index) # 输出：3
len
len方法返回元组中元素的数量。
my_tuple = ('apple', 'banana', 'orange')
length = len(my_tuple)
print(length) # 输出：3
tuple
tuple函数用于将一个可迭代对象转换为元组。
my_list = [1, 2, 3]
my_tuple = tuple(my_list)
print(my_tuple) # 输出：(1, 2, 3)
zip
zip函数将多个可迭代对象的对应元素打包成元组，返回一个包含这些元组的迭代器。
fruits = ('apple', 'banana', 'orange')
quantities = (5, 2, 3)
prices = (1.2, 1.5, 0.8)
# 将三个元组打包成一个迭代器
inventory = zip(fruits, quantities, prices)
# 遍历迭代器中的元素
for item in inventory:
print(item)
# 输出：
# ('apple', 5, 1.2)
# ('banana', 2, 1.5)
# ('orange', 3, 0.8)
sorted

---

<!-- p.134 -->

sorted函数返回一个按指定顺序排序后的可迭代对象，可以接收一个关键字参数key来指定排序的关键字。
my_tuple = (3, 2, 1)
sorted_tuple = sorted(my_tuple)
print(sorted_tuple) # 输出：[1, 2, 3]
# 按绝对值大小排序
my_tuple = (-3, 2, -1)
sorted_tuple = sorted(my_tuple, key=abs)
print(sorted_tuple) # 输出：[-1, 2, -3]
reversed
reversed函数返回一个迭代器，包含按相反顺序排列的可迭代对象中的元素。
my_tuple = ('apple', 'banana', 'orange')
reversed_tuple = reversed(my_tuple)
for item in reversed_tuple:
print(item)
# 输出：
# orange
# banana
# apple
继续
max
max函数返回可迭代对象中最大的元素，可以接收一个关键字参数key来指定比较的关键字。
my_tuple = (3, 2, 1)
max_element = max(my_tuple)
print(max_element) # 输出：3
# 按绝对值大小比较
my_tuple = (-3, 2, -1)
max_element = max(my_tuple, key=abs)
print(max_element) # 输出：-3
min
min函数返回可迭代对象中最小的元素，可以接收一个关键字参数key来指定比较的关键字。
my_tuple = (3, 2, 1)
min_element = min(my_tuple)
print(min_element) # 输出：1
# 按绝对值大小比较
my_tuple = (-3, 2, -1)
min_element = min(my_tuple, key=abs)
print(min_element) # 输出：-1
sum
sum函数返回可迭代对象中所有元素的和，可以接收一个可选参数start指定求和的起始值。
my_tuple = (3, 2, 1)
sum_value = sum(my_tuple)
print(sum_value) # 输出：6
# 指定求和的起始值为5
my_tuple = (3, 2, 1)
sum_value = sum(my_tuple, 5)
print(sum_value) # 输出：11
all
all函数返回可迭代对象中所有元素都为真值（即不为False、0、None等）时返回True，否则返回False。
my_tuple = (1, 2, 3)
result = all(my_tuple)
print(result) # 输出：True
my_tuple = (1, 2, 0)
result = all(my_tuple)

---

<!-- p.135 -->

4.10 字典
print(result) # 输出：False
any
any函数返回可迭代对象中至少有一个元素为真值（即不为False、0、None等）时返回True，否则返回
False。
my_tuple = (0, False, None)
result = any(my_tuple)
print(result) # 输出：False
my_tuple = (0, False, 1)
result = any(my_tuple)
print(result) # 输出：True
Python字典（dictionary）是一个无序的键值对集合。Python中有许多内置函数可以操作字典。
以下是一些常用的函数及其示例：
创建字典
# 创建一个空字典
my_dict = {}
# 创建一个非空字典
my_dict = {'apple': 1, 'banana': 2, 'orange': 3}
访问字典
# 获取字典中指定键对应的值
value = my_dict['apple']
print(value) # 输出：1
# 使用get()方法获取字典中指定键对应的值
value = my_dict.get('banana')
print(value) # 输出：2
# 获取字典中所有键的列表
keys = list(my_dict.keys())
print(keys) # 输出：['apple', 'banana', 'orange']
# 获取字典中所有值的列表
values = list(my_dict.values())
print(values) # 输出：[1, 2, 3]
修改字典
# 修改字典中指定键对应的值
my_dict['apple'] = 4
print(my_dict) # 输出：{'apple': 4, 'banana': 2, 'orange': 3}
# 使用update()方法修改字典中的值
my_dict.update({'apple': 5, 'orange': 6})
print(my_dict) # 输出：{'apple': 5, 'banana': 2, 'orange': 6}
删除字典
# 删除字典中指定键值对
del my_dict['apple']
print(my_dict) # 输出：{'banana': 2, 'orange': 6}
# 删除字典中所有键值对

---

<!-- p.136 -->

my_dict.clear()
print(my_dict) # 输出：{}
其他函数
# 获取字典中键值对的数量
num_items = len(my_dict)
print(num_items) # 输出：0
# 检查字典中是否存在指定键
if 'apple' in my_dict:
print('Yes') # 输出：No
# 复制字典
new_dict = my_dict.copy()
print(new_dict) # 输出：{}
遍历字典
# 遍历字典中所有键值对
for key, value in my_dict.items():
print(key, value)
# 遍历字典中所有键
for key in my_dict.keys():
print(key)
# 遍历字典中所有值
for value in my_dict.values():
print(value)
设置默认值
# 使用setdefault()方法设置默认值
my_dict.setdefault('apple', 0)
print(my_dict) # 输出：{'banana': 2, 'orange': 6, 'apple': 0}
合并字典
# 使用update()方法合并字典
dict1 = {'apple': 1, 'banana': 2}
dict2 = {'orange': 3, 'pear': 4}
dict1.update(dict2)
print(dict1) # 输出：{'apple': 1, 'banana': 2, 'orange': 3, 'pear': 4}
# 使用**运算符合并字典
dict1 = {'apple': 1, 'banana': 2}
dict2 = {'orange': 3, 'pear': 4}
dict3 = {**dict1, **dict2}
print(dict3) # 输出：{'apple': 1, 'banana': 2, 'orange': 3, 'pear': 4}
字典推导式
# 创建字典推导式
my_dict = {i: i*2 for i in range(5)}
print(my_dict) # 输出：{0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
反转字典
# 反转字典中的键值对
my_dict = {'apple': 1, 'banana': 2, 'orange': 3}
reversed_dict = {value: key for key, value in my_dict.items()}
print(reversed_dict) # 输出：{1: 'apple', 2: 'banana', 3: 'orange'}

---

<!-- p.137 -->

4.11 集合
排序字典
# 按键排序
my_dict = {'apple': 1, 'banana': 2, 'orange': 3}
sorted_dict = {key: my_dict[key] for key in sorted(my_dict)}
print(sorted_dict) # 输出：{'apple': 1, 'banana': 2, 'orange': 3}
# 按值排序
my_dict = {'apple': 1, 'banana': 2, 'orange': 3}
sorted_dict = {key: value for key, value in sorted(my_dict.items(), key=lambda
item: item[1])}
print(sorted_dict) # 输出：{'apple': 1, 'banana': 2, 'orange': 3}
过滤字典
# 过滤字典中满足条件的键值对
my_dict = {'apple': 1, 'banana': 2, 'orange': 3}
filtered_dict = {key: value for key, value in my_dict.items() if value > 1}
print(filtered_dict) # 输出：{'banana': 2, 'orange': 3}
计数器
# 使用collections模块中的Counter类创建计数器
from collections import Counter
my_list = ['apple', 'banana', 'apple', 'orange', 'banana', 'apple']
my_counter = Counter(my_list)
print(my_counter) # 输出：Counter({'apple': 3, 'banana': 2, 'orange': 1})
# 获取计数器中指定元素的数量
count = my_counter['apple']
print(count) # 输出：3
# 获取计数器中出现次数最多的元素和出现次数
most_common = my_counter.most_common(1)
print(most_common) # 输出：[('apple', 3)]
以下是Python set对象支持的一些常用方法：
add(): 将一个元素添加到set中，如果元素已经存在，什么都不会发生。
fruits = {'apple', 'banana', 'orange'}
fruits.add('kiwi')
print(fruits) # {'orange', 'banana', 'kiwi', 'apple'}
clear(): 移除set中的所有元素。
fruits = {'apple', 'banana', 'orange'}
fruits.clear()
print(fruits) # set()
copy(): 返回set的一个副本。
fruits = {'apple', 'banana', 'orange'}
fruits_copy = fruits.copy()
print(fruits_copy) # {'orange', 'banana', 'apple'}
difference(): 返回一个包含set和另一个set或iterable中不同元素的新set。也可以直接减
eg:fruits - more_fruits
fruits = {'apple', 'banana', 'orange'}

---

<!-- p.138 -->

more_fruits = {'banana', 'kiwi', 'pineapple'}
diff_fruits = fruits.difference(more_fruits)
print(diff_fruits) # {'orange', 'apple'}
discard(): 从set中移除一个元素，如果元素不存在，什么都不会发生。
fruits = {'apple', 'banana', 'orange'}
fruits.discard('banana')
print(fruits) # {'orange', 'apple'}
intersection(): 返回一个包含set和另一个set或iterable中共同元素的新set。也可以直接交
eg:fruits & more_fruits
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
common_fruits = fruits.intersection(more_fruits)
print(common_fruits) # {'banana'}
isdisjoint(): 如果set和另一个set或iterable没有共同元素，返回True，否则返回False。也可以直
接交然后判断 eg:return fruits & more_fruits == set()
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'kiwi', 'pineapple'}
print(fruits.isdisjoint(more_fruits)) # True
issubset(): 如果set是另一个set的子集，返回True，否则返回False。
也可以直接交然后判断是不是等于自身 eg:return fruits & more_fruits == fruits
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'orange', 'kiwi', 'pineapple'}
print(fruits.issubset(more_fruits)) # False
issuperset(): 如果set是另一个set的超集，返回True，否则返回False。
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'orange'}
print(fruits.issuperset(more_fruits)) # True
pop(): 移除并返回set中的一个元素，如果set为空，抛出KeyError异常。
fruits = {'apple', 'banana', 'orange'}
print(fruits.pop()) # 'orange'
print(fruits) # {'apple', 'banana'}
remove(): 从set中移除一个元素，如果元素不存在，抛出KeyError异常。
fruits = {'apple', 'banana', 'orange'}
fruits.remove('banana')
print(fruits) # {'orange', 'apple'}
symmetric_difference(): 返回一个包含set和另一个set或iterable中不重复元素的新set
symmetric_difference_update(): 将set和另一个set或iterable中不重复的元素更新到set中。
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
fruits.symmetric_difference_update(more_fruits)
print(fruits) # {'orange', 'kiwi', 'pineapple', 'apple'}
union(): 返回一个包含set和另一个set或iterable中所有元素的新set。
不可以+，除了 union() 方法，我们还可以使用 | 运算符来实现两个 set 的并集
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
all_fruits = fruits.union(more_fruits)
print(all_fruits) # {'kiwi', 'apple', 'pineapple', 'orange', 'banana'}

---

<!-- p.139 -->

4.12 字符串处理函数
4.13 callable()
update(): 将set和另一个set或iterable中所有元素更新到set中。
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
fruits.update(more_fruits)
print(fruits) # {'kiwi', 'apple', 'pineapple', 'orange', 'banana'}
difference_update(): 将set和另一个set或iterable中不同的元素更新到set中。
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
fruits.difference_update(more_fruits)
print(fruits) # {'orange', 'apple'}
intersection_update(): 将set和另一个set或iterable中共同的元素更新到set中。
fruits = {'apple', 'banana', 'orange'}
more_fruits = {'banana', 'kiwi', 'pineapple'}
fruits.intersection_update(more_fruits)
print(fruits) # {'banana'}
大小写处理
s,s1 = "aaaBBBccc", "123456"
s.upper() # 将字符串全部大写 AAABBBCCC
s.lower() # 将字符串全部小写 aaabbbccc
s.swapcase() # 将s大小写反转 AAAbbbCCC
字符判断
isdigit() , isnumeric # 判断字符串中是否全是数字字符
print(list(map(lambda x:x.isdigit(),[Z,Z2]))) # [False, True]
isdigit：是否为数字字符，包括Unicode数字，单字节数字，双字节全角数字，不包括汉字数字，罗马数
字、小数
isnumeric：是否所有字符均为数值字符，包括Unicode数字、双字节全角数字、罗马数字、汉字数字，不包
括小数。
s.isalpha() # 判断字符串中是否全为字母
s.isalnum() # 判断字符串中是否全为字母或者数字
## 判断一个对象能不能调用
def func():
pass
class Foo:
pass
print(callable(Foo)) ## true
print(callable(func)) ## true

---

<!-- p.140 -->

4.14 dir()----查看属性
4.15 enumerate()
4.16 eval()
4.17 frozenset()
4.18 hash()
class Foo:
pass
obj = Foo()
print(dir(obj)) ## 查看obj的属性
'''
['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__',
'__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__',
'__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__',
'__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__',
'__str__', '__subclasshook__', '__weakref__']
'''
## 既能拿到索引，又能拿到值
lis = ['a','b','c','d','f']
for i,v in enumerate(lis):
print(i,v)
# 0 a
# 1 b
# 2 c
# 3 d
# 4 f
## 执行字符串里的表达式
res = eval('1 + 2')
res = eval('{'name':'aini','age':22}')
print(res)
## {'name':'aini','age':22}
## 拿到的就是字典类型
s = frozenset({1,2,3,4,5,6}) ## 得到不可变集合
## 传入不可变类型，得到一个hash值
res = hash('aini')
print(res) ## -3947223962220906649

---

<!-- p.141 -->

4.19 help()
4.20 isinstance()
四，Python进阶知识
1，编码相关
1.1 指定默认的读文件的解码格式保证不乱码
注：Python3默认用utf-8解码； Python2用ASCII码解码
2， 读写文件
计算机文件分为两种：二进制文件(没有统一的字符编码) 纯文本文件(有统一的编码，可以被看做存储
在磁盘上的长字符串)
## 查看文档注释
## 判断一个对象是不是一个类的实例
class Foo:
pass
obj = Foo()
## 判断obj是不是Foo的实例化
isinstance(obj,Foo)
## 判断列表，字典都可以用
isinstance([],list)
isinstance({{'name':'aini','age':22}},dict)
这不是注释，第一行是固定格式 #coding:用什么编码格式读文件
# coding:utg-8 (如果写代码时指定则就是用什么方式编码，如果读文件时指定，则以什么格式解码)
# 代码内容
#Python3里的str类型默认直接存成Unicode所以不存在乱码
#·若要保证Python2的str类型也不乱码
x = u"艾尼你好" # 前面加上u,意思就是Unicode编码
打开文件的模式:
mode 解释
r 只读【默认模式，文件必须存在，不存在则抛出异常】
w 只写，写之前会清空文件的内容，如果文件不存在，会创建新文件
a 追加的方式，在原本内容中继续写，如果文件不存在，则会创建新文件
r+ 可读可写
w+ 打开一个文件用于读写。如果该文件已存在则将其覆盖。如果该文件不存在，创建新文件。
a+ 打开一个文件用于读写。如果该文件已存在，文件指针将会放在文件的结尾。文件打开时会是追加模式。
如果该文件不存在，创建新文件用于读写。
b rb、wb、ab、rb+、wb+、ab+意义和上面一样，用于二进制文件操作

---

<!-- p.142 -->

2.1 控制文件读写内容的模式：t和b
2.2 文件操作的模式
3，函数参数详解
# 强调：读写不能单独使用，必须跟r/w/a连用
open()方法，with 语法
1，t模式(默认的模式)
# 读写都以str（Unicode）为单位
# 必须指定encoding="utf-8"
# 必须是文本文件才可以指定编码
2，b模式
# 是对字节进行操作
# 不用指定编码
#文件操作基本流程
1，打开文件
# window系统路径分割问题
# 解决方案一：推荐
f = open(r'C:\a\b\c\aini.txt')
# 解决方案二：open这函数已经解决好了，右斜杠也可以
f = open('C:/a/b/c/aini.txt)
2，操作文件
f = open('./aini.txt',mode='r',encoding='utf-8')
res = f.read()
# 指针会停在最后，所以第二次读的时候没内容，需要重新打开文件，重新读取
# 会读取所有内容
3，关闭文件
f.close() #回收操作系统资源
# 文件操作模式
# r w a 默认都是t模式，对文本进行操作(rt,wt,at)
# rb wb ab 对字节进行操作
# a 是追加模式，会往文件末尾开始写，w会把源文件清空掉
# rt+ 可读可写，文件不存在直接报错
# wt+ 可读可写，
# 指针移动
# 指针移动的单位都是bytes字节为单位
# 只有一种特殊情况
# t模式下的read(n),n代表的是字符个数
with open('./aini.txt',mode='rt',encoding='utf-8') as f:
f.read(4) # 四个字符
### 注意： 只有0模式在t模式下使用
f.seek(n,模式) # n值得是指针移动的字节个数，n可以是负数，可以倒着移动
# 模式
# 0 参照的是文件开头位置
# 1 参照的是当前指针的所造位置
# 2 参照物是文件末尾
f.tell ## 获取指针当前位置

---

<!-- p.143 -->

3.1 位置参数--------关键字参数---------混合使用
3.2 默认参数------位置参数与默认参数混用
1，位置实参:在函数调用阶段， 按照从左到有的顺序依次传入的值
# 特点：按照顺序与形参一一对应
2 关键字参数
# 关键字实参：在函数调用阶段，按照key=value的形式传入的值
# 特点：指名道姓给某个形参传值，可以完全不参照顺序
def func(x,y):
print(x,y)
func(y=2,x=1) # 关键字参数
func(1,2) # 位置参数
3，混合使用，强调
# 1、位置实参必须放在关键字实参前
def func(x,y):
print(x,y)
func(1,y=2)
func(y=2,1)
# 2、不能能为同一个形参重复传值
def func(x,y):
print(x,y)
func(1,y=2,x=3)
func(1,2,x=3,y=4)
4，默认参数
# 默认形参：在定义函数阶段，就已经被赋值的形参，称之为默认参数
# 特点：在定义阶段就已经被赋值，意味着在调用阶段可以不用为其赋值
def func(x,y=3):
print(x,y)
func(x=1)
func(x=1,y=44444)
def register(name,age,gender='男'):
print(name,age,gender)
register('三炮',18)
register('二炮',19)
register('大炮',19)
register('没炮',19,'女')
5，位置形参与默认形参混用，强调：
# 1、位置形参必须在默认形参的左边
def func(y=2,x): # 错误写法
pass
# 2、默认参数的值是在函数定义阶段被赋值的，准确地说被赋予的是值的内存地址
# 示范1：
m=2

---

<!-- p.144 -->

3.3 可变长度的参数
def func(x,y=m): # y=>2的内存地址
print(x,y）
m=3333333333333333333
func(1)
# 3、虽然默认值可以被指定为任意数据类型，但是不推荐使用可变类型
# 函数最理想的状态：函数的调用只跟函数本身有关系，不外界代码的影响
m = [111111, ]
def func(x, y=m):
print(x, y)
m.append(3333333)
m.append(444444)
m.append(5555)
func(1)
func(2)
func(3)
def func(x,y,z,l=None):
if l is None:
l=[]
l.append(x)
l.append(y)
l.append(z)
print(l)
func(1,2,3)
func(4,5,6)
new_l=[111,222]
func(1,2,3,new_l)
6，可变长度的参数（*与**的用法）
# 可变长度指的是在调用函数时，传入的值（实参）的个数不固定
# 而实参是用来为形参赋值的，所以对应着，针对溢出的实参必须有对应的形参来接收
6.1 可变长度的位置参数
# I：*形参名：用来接收溢出的位置实参，溢出的位置实参会被*保存成元组的格式然后赋值紧跟其后的
形参名
# *后跟的可以是任意名字，但是约定俗成应该是args
def func(x,y,*z): # z =（3,4,5,6）
print(x,y,z)
func(1,2,3,4,5,6)
def my_sum(*args):
res=0
for item in args:
res+=item
return res
res=my_sum(1,2,3,4,)

---

<!-- p.145 -->

print(res)
# II: *可以用在实参中，实参中带*，先*后的值打散成位置实参
def func(x,y,z):
print(x,y,z)
func(*[11,22,33]) # func(11，22，33)
func(*[11,22]) # func(11，22)
l=[11,22,33]
func(*l)
# III: 形参与实参中都带*
def func(x,y,*args): # args=(3,4,5,6)
print(x,y,args)
func(1,2,[3,4,5,6])
func(1,2,*[3,4,5,6]) # func(1,2,3,4,5,6)
func(*'hello') # func('h','e','l','l','o')
6.2 可变长度的关键字参数
# I：**形参名：用来接收溢出的关键字实参，**会将溢出的关键字实参保存成字典格式，然后赋值给紧
跟其后的形参名
# **后跟的可以是任意名字，但是约定俗成应该是kwargs
def func(x,y,**kwargs):
print(x,y,kwargs)
func(1,y=2,a=1,b=2,c=3)
# II: **可以用在实参中(**后跟的只能是字典)，实参中带**，先**后的值打散成关键字实参
def func(x,y,z):
print(x,y,z)
func(*{'x':1,'y':2,'z':3}) # func('x','y','z')
func(**{'x':1,'y':2,'z':3}) # func(x=1,y=2,z=3)
# 错误
func(**{'x':1,'y':2,}) # func(x=1,y=2)
func(**{'x':1,'a':2,'z':3}) # func(x=1,a=2,z=3)
# III: 形参与实参中都带**
def func(x,y,**kwargs):
print(x,y,kwargs)
func(y=222,x=111,a=333,b=444)
func(**{'y':222,'x':111,'a':333,'b':4444})
# 混用*与**：*args必须在**kwargs之前
def func(x,*args,**kwargs):
print(args)
print(kwargs)
func(1,2,3,4,5,6,7,8,x=1,y=2,z=3)
def index(x,y,z):

---

<!-- p.146 -->

3.4 函数的类型提示
4，装饰器
4.1 装饰器的一步步实现
print('index=>>> ',x,y,z)
def wrapper(*args,**kwargs): #args=(1,) kwargs={'z':3,'y':2}
index(*args,**kwargs)
# index(*(1,),**{'z':3,'y':2})
# index(1,z=3,y=2)
wrapper(1,z=3,y=2) # 为wrapper传递的参数是给index用的
## : 后面是提示信息，可以随意写
def regidter(name:"不能写艾尼",age:"至少18岁")：
print(name)
print(age)
def register(name:str,age:int,hobbies:tuple)->int: # 返回值类型为 int
print(name)
print(age)
print(hobbies)
# 添加提示功能的同时，再添加默认值
def register(name:str = 'aini',age:int = 18 ,hobbies:tuple)->int: # 返回值类型为
int
print(name)
print(age)
print(hobbies)
装饰器:
装饰器就是使用创建一个闭包函数,在闭包函数内调用目标函数，可以达到不改动目标函数的同时,增加额
外的功能
写法:
def outer(func):
def inner():
print("xxx")
func()
print("xxxx")
return inner
@outer
def sleep():
import random
import time
print("xxx")
time.sleep(random.randint(1,5))
sleep()

---

<!-- p.147 -->

## 装饰器：装饰器定义一个函数，该函数是用来为其他函数添加额外的工能
## 装饰器就是不修改源代码以及调用方式的基础上增加新功能
## 开放封闭原则
# 开放：指的是对拓展工能是开放的
# 封闭： 指的是对修改源代码是封闭的
## 添加一个计算代码运行时间的工能（修改了源代码）
import time
def index(name,age):
start = time.time()
time.sleep(3)
print('我叫%s,今年%s岁'%(name,age))
end = time.time()
print(end - start)
index(age = 18,name = 'aini')
# --------------------------------------------------------------------------
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def wrapper():
start = time.time()
index1(name="aini", age=18)
time.sleep(3)
end = time.time()
print(end - start)
wrapper()
# 解决了修改原函数，但是也改变了函数调用方式
# -------------------------------------------------------------------------------
-------
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def wrapper(name,age):
start = time.time()
index1(name, age)
time.sleep(3)
end = time.time()
print(end - start)
wrapper('aini',18)
# -------------------------------------------------------------------------------
----
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def wrapper(*args,**kwargs):
start = time.time()
index1(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)

---

<!-- p.148 -->

wrapper('aini',age = 18)
# -------------------------------------------------------------------------------
-----
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def outer():
func = index
def wrapper(*args,**kwargs):
start = time.time()
fun(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)
return wrapper
f = outer() # f本质就是wrapper函数
### 继续改进
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def outer(fun):
def wrapper(*args,**kwargs):
start = time.time()
fun(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)
return wrapper
f = outer(index1) # f本质就是wrapper函数
f(name='aini',age=22)
# 继续改进，偷梁换柱
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
def outer(fun):
def wrapper(*args,**kwargs):
start = time.time()
fun(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)
return wrapper
index1 = outer(index1) # f本质就是wrapper函数
index1(name='aini',age=22) # 新功能加上了，也没有修改函数的调用方式
# ---------------------------------------------------------

---

<!-- p.149 -->

4.2 装饰器最终版本
4.3 装饰器语法糖
# 被装饰函数有返回值
########### 装饰器最终版本
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
return [name,age] # 有返回值
def outer(fun):
def wrapper(*args,**kwargs):
start = time.time()
arg = fun(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)
return arg # 返回index1 的返回值
return wrapper
index1 = outer(index1) # f本质就是wrapper函数
res = index1(name='aini',age=22) # 新功能加上了，也没有修改函数的调用方式，把原函数的返回
值也拿到了
# -------------------------------------------------------------------------------
-------------------
def outer(fun):
def wrapper(*args,**kwargs):
start = time.time()
arg = fun(*args,**kwargs)
time.sleep(3)
end = time.time()
print(end - start)
return arg # 返回index1 的返回值
return wrapper
@outer
def index1(name,age):
print('我叫%s,今年%s岁' % (name, age))
return [name,age] # 有返回值
# -----------------------------------------------
# 与原函数伪装的更像一点
from functools import wraps # 用于把原函数的属性特征赋值给另一个函数
def outer(fun):
@wraps(fun) # 可以把fun函数的所有属性特征加到wrapper函数身上
def wrapper(*args,**kwargs):
# wrapper.__name__ = fun.__name__
# wrapper.__doc__ = fun.__doc__
# 手动赋值麻烦
start = time.time()
arg = fun(*args,**kwargs)

---

<!-- p.150 -->

4.4 有参装饰器
4.4.1 不用语法糖
4.4.2 语法糖01
time.sleep(3)
end = time.time()
print(end - start)
return arg # 返回index1 的返回值
return wrapper
@outer
def index1(name,age):
'''我是index1''' # 通过help(index)函数来查看 文档信息，可以通过index.__doc__ =
'xxxxx' 来给某个函数赋值文档信息
# 通过 index__name__ 可以获得函数的名字，也可以对其进行赋值
print('我叫%s,今年%s岁' % (name, age))
return [name,age] # 有返回值
### 不用语法糖
def auth(func,db_type):
def wrapper(*args,**kwargs):
name = input('your name:').strip()
pwd = input('your password:').strip()
if db_type == 'file':
print('基于文件验证')
if name == 'aini' and pwd == 'aini123':
print('login success')
res = func(*args,**kwargs)
return res
else:
print('用户名或者密码错误!!')
elif db_type == 'mysql':
print('基于mysql验证')
elif db_type == 'ldap':
print('基于ldap验证')
else:
print('基于其他途径验证')
return wrapper
def index(x,y):
print('index->>%s:%s'%(x,y))
index = auth(index,'file')
index('aini',22)
#---------------------------------------------------------------------
# 语法糖01
def auth(db_type = "file"):
def deco(func):
def wrapper(*args,**kwargs):
name = input('your name:').strip()

---

<!-- p.151 -->

4.4.3 标准语法糖
pwd = input('your password:').strip()
if db_type == 'file':
print('基于文件验证')
if name == 'aini' and pwd == 'aini123':
print('login success')
res = func(*args,**kwargs)
return res
else:
print('用户名或者密码错误!!')
elif db_type == 'mysql':
print('基于mysql验证')
elif db_type == 'ldap':
print('基于ldap验证')
else:
print('基于其他途径验证')
return wrapper
return deco
deco = auth(db_type = 'file')
@deco
def index(x,y):
print('index->>%s:%s'%(x,y))
index('aini',22)
deco = auth(db_type = 'mysql')
@deco
def index(x,y):
print('index->>%s:%s'%(x,y))
index('aini',22)
# -------------------------------------------------------------------------------
--
# 标准语法糖模板
def auth(外界传递的参数):
def deco(func):
def wrapper(*args,**kwargs):
'''自己扩展的功能'''
res = func(*args,**kwargs)
return res
return wrapper
return deco
@auth(外界传递的参数)
def index(x,y):
print(x,y)
return(x,y)
# 标准语法糖02（例子）
def auth(db_type = "file"):
def deco(func):
def wrapper(*args,**kwargs):
name = input('your name:').strip()
pwd = input('your password:').strip()

---

<!-- p.152 -->

5， 迭代器
5.1 基础知识
1，迭代器：迭代取值的工具，迭代是重复的过程，每一次重复都是基于上次的结果而继续的，单纯的重
复不是迭代
if db_type == 'file':
print('基于文件验证')
if name == 'aini' and pwd == 'aini123':
print('login success')
res = func(*args,**kwargs)
return res
else:
print('用户名或者密码错误!!')
elif db_type == 'mysql':
print('基于mysql验证')
elif db_type == 'ldap':
print('基于ldap验证')
else:
print('基于其他途径验证')
return wrapper
return deco
@auth(db_type = 'file')
def index(x,y):
print('index->>%s:%s'%(x,y))
index('aini',22)
@auth(db_type = 'file')
def index(x,y):
print('index->>%s:%s'%(x,y))
index('aini',22)
# 可迭代对象： 但凡内置有__iter__()方法的都称之为可迭代对象
# 字符串---列表---元祖---字典---集合---文件操作 都是可迭代对象
# 调用可迭代对象下的__iter__方法将其转换为可迭代对象
d = {'a':1, 'b':2, 'c':3}
d_iter = d.__iter__() # 把字典d转换成了可迭代对象
# d_iter.__next__() # 通过__next__()方法可以取值
print(d_iter.__next__()) # a
print(d_iter.__next__()) # b
print(d_iter.__next__()) # c
# 没值了以后就会报错， 抛出异常StopIteration
#-----------------------------------------------
d = {'a':1, 'b':2, 'c':3}
d_iter = d.__iter__()

---

<!-- p.153 -->

5.2 迭代器与for循环工作原理
6，生成器（本质就是迭代器）
while True:
try:
print(d_iter.__next__())
except StopIteration:
break
# 对同一个迭代器对象，取值取干净的情况下第二次取值的时候去不了，没值，只能造新的迭代器
#可迭代对象与迭代器详解
#可迭代对象：内置有__iter__() 方法对象
# 可迭代对象.__iter__(): 得到可迭代对象
#迭代器对象：内置有__next__() 方法
# 迭代器对象.__next__()：得到迭代器的下一个值
# 迭代器对象.__iter__(): 得到的值迭代器对象的本身（调跟没调一个样）-----------> 为
了保证for循环的工作
# for循环工作原理
d = {'a':1, 'b':2, 'c':3}
d_iter = d.__iter__()
# 1，d.__iter__() 方法得到一个跌倒器对象
# 2,迭代器对象的__next__()方法拿到返回值，将该返回值赋值给k
# 3,循环往复步骤2，直到抛出异常，for循环会捕捉异常并结束循坏
for k in d:
print(k)
# 可迭代器对象不一定是迭代器对象------------迭代器对象一定是可迭代对象
# 字符串---列表---元祖---字典---集合只是可迭代对象，不是迭代器对象、
# 文件操作时迭代器对象也是可迭代对象
# 函数里包含yield,并且调用函数以后就能得到一个可迭代对象
def test():
print('第一次')
yield 1
print('第二次')
yield 2
print('第三次')
yield 3
print('第四次')
g = test()
print(g) # <generator object test at 0x0000014C809A27A0>
g_iter = g.__iter__()
res1 = g_iter.__next__() # 第一次
print(res1) # 1
res2 = g_iter.__next__() # 第二次
print(res2) # 2
res3 = g_iter.__next__() # 第三次
print(res3) # 3

---

<!-- p.154 -->

1，yield 表达式
2， 三元表达式
3，列表生成式
# 补充
len(s) -------> s.__len__()
next(s) ------> s.__next__()
iter(d) -------> d.__iter__()
def person(name):
print("%s吃东西啦！！"%name)
while True:
x = yield None
print('%s吃东西啦---%s'%(name,x))
g = person('aini')
# next(g) =============== g.send(None)
next(g)
next(g)
# send()方法可以给yield传值
# 不能在第一次运行时用g.send()来传值，需要用g.send(None)或者next(g) 来初始化，第二次开始可
以用g.send("值")来传值
g.send("雪糕") # aini吃东西啦---雪糕
g.send("西瓜") # aini吃东西啦---西瓜
x = 10
y = 20
res = x if x > y else y
# 格式
条件成立时返回的值 if 条件 else 条件不成立时返回的值
l = ['aini_aaa','dilnur_aaa','donghua_aaa','egon']
res = [name for name in l if name.endswith('aaa')]
print(res)
# 语法： [结果 for 元素 in 可迭代对象 if 条件]
l = ['aini_aaa','dilnur_aaa','donghua_aaa','egon']
l = [name.upper() for name in l]
print(l)
l = ['aini_aaa','dilnur_aaa','donghua_aaa','egon']
l = [name.replace('_aaa','') for name in l if name.endswith('_aaa')]
print(l)

---

<!-- p.155 -->

4，其他生成器（——没有元祖生成式——）
5，二分法
6，匿名函数与lambdaj
### 字典生成器
keys = ['name','age','gender']
res = {key: None for key in keys}
print(res) # {'name': None, 'age': None, 'gender': None}
items = [('name','aini'),('age',22),('gender','man')]
res = {k:v for k,v in items}
print(res)
## 集合生成器
keys = ['name','age','gender']
set1 = {key for key in keys}
## 没有元祖生成器
g = (i for i in range(10) if i % 4 == 0 ) ## 得到的是一个迭代器
#### 统计文件字符个数
with open('aini.txt', mode='rt', encoding= 'utf-8') as f:
res = sum(len(line) for line in f)
print(res)
l = [-10,-6,-3,0,1,10,56,134,222,234,532,642,743,852,1431]
def search_num(num,list):
mid_index = len(list) // 2
if len(list) == 0:
print("没找到")
return False
if num > list[mid_index]:
list = list[mid_index + 1 :]
search_num(num,list)
elif num < list[mid_index]:
list = list[:mid_index]
search_num(num, list)
else:
print('找到了' , list[mid_index])
search_num(743,l)
## 定义
res = lambda x,y : x+y
## 调用
(lambda x,y : x+y)(10,20) # 第一种方法
res(10,20) ## 第二种方法
##应用场景
salary = {
'aini':20000,

---

<!-- p.156 -->

7，模块
7.1 写模块时测试
'aili':50000,
'dilnur':15000,
'hahhaha':42568,
'fdafdaf':7854
}
res = max(salary ,key= lambda x : salary[x])
print(res)
## 内置模块
## 第三方模块
## 自定义模块
## 模块的四种形式
1， 使用Python编写的py文件
2， 已被编译为共享库或DLL的C或C++扩展
3， 把一系列模块组织到一起的文件夹（文件夹下面有个__init__.py 该文件夹称为包）
3， 使用C编写并链接到Python解释器的内置模块
import foo
## 首次导入模块会发生什么？
1，执行foo.py
2, 产生foo.py的命名空间
3，在当前文件中产生的有一个名字foo,改名字指向2中产生的命名空间
## 无论是调用还是修改与源模块为准，与调用位置无关
## 导入模块规范
1 Python内置模块
2，Python第三方模块
3，自定义模块
## 起别名
import foo as f
## 自定义模块命名应该纯小写+下划线
## 可以在函数内导入模块
# 每个Python文件内置了__name__,指向Python文件名
# 当foo.py 被运行时，
__name__ = "__main__"
# 当foo.py 被当做模块导入时，
__name__ != "__main__"
##### 测试时可以if判断,在foo.py文件中写以下判断
if __name__ == "__main__" :
## 你的测试代码

---

<!-- p.157 -->

7.2 from xxx import xxx
7.3 从一个模块导入所有
7.4 sys.path 模块搜索路径优先级
# from foo import x 发生什么事情
1， 产生一个模块的命名空间
2， 运行foo.py 产生，将运行过程中产生的名字都丢到命名空间去
3， 在当前命名空间拿到一个名字，改名字指向模块命名空间
#不太推荐使用
form foo import *
# 被导入模块有个 __all__ = []
__all__ = [] # 存放导入模块里的所有变量和函数， 默认放所有的变量和函数，也可以手动修改
foo.py
__all__ = ['x','change']
x = 10
def change():
global x
x = 20
a = 20
b = 30
run.py
from foo import * ## * 导入的是foo.py里的 __all__ 列表里的变量和函数
print(x)
change()
print(a) # 会报错，因为foo.py 里的 __all__ 列表里没有a变量
1， 内存（内置模块）
2， 从硬盘查找
import sys
# 值为一个列表，存放了一系列的文件夹
# 其中第一个文件夹是当前执行所在的文件夹
# 第二个文件夹当不存在，因为这不是解释器存放的，是pycharm添加的
print(sys.path)
# sys.path 里放的就是模块的存放路径查找顺序
[
'E:\\Desktop\\python全栈\\模块', 'E:\\Desktop\\python全栈', 'D:\\软件
\\pycharm\\PyCharm 2021.3.1\\plugins\\python\\helpers\\pycharm_display', 'D:\\软
件\\python\\python310.zip', 'D:\\软件\\python\\DLLs', 'D:\\软件\\python\\lib',
'D:\\软件\\python', 'C:\\Users\\艾尼-
aini\\AppData\\Roaming\\Python\\Python310\\site-packages', 'D:\\软件
\\python\\lib\\site-packages', 'D:\\软件\\python\\lib\\site-packages\\win32',
'D:\\软件\\python\\lib\\site-packages\\win32\\lib', 'D:\\软件\\python\\lib\\site-
packages\\Pythonwin', 'D:\\软件\\pycharm\\PyCharm
2021.3.1\\plugins\\python\\helpers\\pycharm_matplotlib_backend'
]

---

<!-- p.158 -->

7.5 sys.modules 查看内存中的模块
7.6 编写规范的模块
8，包（包本身就是模块）
9, 软件开发的目录规范
import sys
print(sys.module) # 是一个字典，存放导入的模块
## 可以判断一个模块是否已经在内存中
print('foo' in sys.module)
"this module is used to ......" # 第一行文档注释
import sys # 导入需要用到的包
x = 1 # 定义全局变量
class foo: # 定义类
pass
def test(): #定义函数
pass
if __name__ == "__main__":
pass
### 包就是一个包含__init__.py的文件夹，包的本质是模块的一种形式，包用来被当做模块导入
### 导入包运行时运行__inti__.py文件里的代码
### 环境变量是以执行文件为准备的，所有的被导入的模块或者说后续的其他的sys.path都是参照执行文件
的sys.path
ATM --------------------------------- # 项目跟目录
bin
start.py ---------------------# 启动程序
config ------------------------- # 项目配置文件
setting.py
db ------------------------------- # 数据库相关的文件夹
db_handle.py
lib ------------------------------ # 共享库（包）
common.py
core ------------------------------# 核心代码逻辑
src.py
api -------------------------------# API有关的文件夹
api.py
log -------------------------------# 记录日志的文件夹
user.log
README --------------------------- # 对软件的解释说明

---

<!-- p.159 -->

10，反射
10.1 什么是反射
10.2 如何实现反射
五，面向对象编程
1，类的定义
__file__ # 当前文件的绝对路径
# 在start.py中运行 print(__file__) ---------------------- E:\Desktop\python全栈
\ATM\bin\start.py
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) ## 这样可以动态拿到根目录
sys.path.append(BASE_DIR) # 把项目根目录加到环境变量了,这样可以很好的导包了
## 如果把运行文件 start.py 直接放在跟文件的目录下，就不需要处理环境变量了
## 反射---------------> 程序运行过程当中，动态的获取对象的信息。
# 通过dir:查看某一个对象可以.出来那些属性来
# 可以通过字符串反射到真正的属性上，得到熟悉值
## 四个内置函数的使用
hasattr() ## 判断属性是否存在
getattr() ## 得到属性
setattr() ## 设置属性
delattr() ## 删除属性
hasattr(obj,'name') ## 判断对象 obj 有没有 name 属性
getattr(obj,;'name',None) ## 得到对象 obj 的 name 属性,如果没有返回 None
setattr(obj,'name','aini') ## 设置对象 obj 的 name 属性为 "aini"
delattr(obj,'name') ## 删除对象 obj 的 name 属性
类的定义和使用:
语法:
定义类:
class 类名称:
类中定义的属性(成员变量)
类中定义的行为(成员方法)
创建类:
对象=类名称()

---

<!-- p.160 -->

成员方法的定义:
语法:
def 方法名(self,形参1，形参2...):
方法体
注意:
1.self关键字是成员方法定义的时候，必须填写的，它用来表示类对象自身的意思
2.当使用类对象调用方法时，self会自动被python传入
3.在方法内部，要想访问类的成员变量，必须使用self
4.self关键字，尽管在参数列表中，但是传参的时候可以忽略它
## 类名驼峰命名
## 类体中可以写任意Python代码，类体代码在定义时就运行
## __dic__ 可以查看类的命名空间
'''
{'__module__': '__main__', 'school': 'donghua', 'adress': 'shanghai', 'local':
<classmethod(<function Student.local at 0x000001BCF418E9E0>)>, 'say_hello':
<staticmethod(<function Student.say_hello at 0x000001BCF418EA70>)>, '__init__':
<function Student.__init__ at 0x000001BCF418EB00>, 'say_score': <function
Student.say_score at 0x000001BCF418EB90>, '__dict__': <attribute '__dict__' of
'Student' objects>, '__weakref__': <attribute '__weakref__' of 'Student'
objects>, '__doc__': None}
'''
class Student:
# 类属性
# 可以被所有的实例对象所共享
school = 'donghua'
adress = 'shanghai'
stu_count = 0 # 统计注册的实例个数
# 类方法
@classmethod
def local(cls):
print(cls.adress)
# 静态方法
# 可以调用类的属性和方法
@staticmethod
def say_hello(str):
print(str)
Student.local()
# 通过构造函数__init__创建对象的属性
def __init__(self,name,age,score):
self.name = name
self.age = age
self.score = score
Student.stu_count += 1
# 创建实例对象方法
def say_score(self):
print(f'{self.name}的分数是{self.score}')
print(Student.say_score) ## <function Student.say_score at 0x00000255F6DDEB90>

---

<!-- p.161 -->

2，封装
2.1 私有属性
s1 = Student('aini',22,80) ## 实例化
Student.say_score(s1) ## aini的分数是80
s1.say_score() ----- ## 本质是 Student.say_score(s1)
## 通过类名可以调用实例方法，需要传递实例进去
## 实例化发生的三件事情
1，先产生一个空对象
2，Python会自动调用 __init__方法
3，返回初始化完的对象
print(s1.__dict__) ------ ## ## {'name': 'aini', 'age': 22, 'score': 80}
封装:
描述: 将现实世界事物在类中描述为属性和方法,即为封装
私有成员:
描述: 现实事物有部分属性和行为时不公开对使用者开放的
定义: 成员变量和成员方法的命名均以__作为开头即可
访问限制:
1.类对象无法访问私有成员
2.类中的其它成员可以访问私有成员
## 在属性或方法前加__前缀，可以对外进行隐藏
## 这种隐藏对外不对内，因为__开头的属性会在类定义阶段检查语法时统一变形
class Foo:
__x = 1
def __test(self):
print('from test')
def f2(self):
print(self.__x) # 1
print(self.__test) ## <bound method Foo.__test of <__main__.Foo object
at 0x000002063304B7F0>>
## 隐藏属性的访问
## Python不推荐此方法
print(Foo._Foo__x) ## 1
print(Foo._Foo__test) ## <function Foo.__test at 0x000001C42976E320>
## 这种变形操作只在检查类语法的时候发生一次，之后定义__定义的属性都不会变形
Foo.__y = 3
print(Foo.__y)

---

<!-- p.162 -->

2.2 property使用
## 第一种类型
## 把函数像普通属性一样调用
class Person:
def __init__(self,name):
self.__name = name
@property
def get_name(self):
return self.__name
aini = Person('aini')
print(aini.get_name) ## 'aini'
## 第二种类型
class Person:
def __init__(self,name):
self.__name = name
def get_name(self):
return self.__name
def set_name(self,val):
if type(val) is not str:
print('必须传入str类型')
return
self.__name = val
## 伪装成数据接口的属性
name = property(get_name,set_name)
aini = Person('aini')
print(aini.name) ## 'aini'
aini.name = 'norah'
print(aini.name) ## 'norah'
## 第三种方法
## 起一个一样的函数名，用不同功能的property装饰
class Person:
def __init__(self,name):
self.__name = name
@property ## name = property(name)
def name(self):
return self.__name
@name.setter
def name(self,val):
if type(val) is not str:

---

<!-- p.163 -->

3，继承
Python里支持多继承
python3里没有继承任何类的类都继承了Object类
Python2 里有经典类和新式类
经典类：没有继承Object ------------------ 新式类：继承了Object
3.1 继承的实现
print('必须传入str类型')
return
self.__name = val
@ name.deleter
def name(self):
print("不能删除")
class Parent1:
pass
class Parent2:
pass
class Sub1(Parent1): ## 单继承
pass
class Sub2(Parent1,Parent2): ## 多继承
pass
print(Sub1.__bases__) ## (<class '__main__.Parent1'>,)
print(Sub2.__bases__) ## (<class '__main__.Parent1'>, <class
'__main__.Parent2'>)
class OldBoyPeople:
school = 'OLDBOY'
def __init__(self, name, age, sex):
self.name = name
self.age = age
self.sex = sex
class Student(OldBoyPeople):
def choose_course(self):
print(f'学生 {self.name}正在选课')
class Teacher(OldBoyPeople):
def __init__(self,name,age,sex,salary,level):
# 调父类的属性就行
OldBoyPeople.__init__(self,name,age,sex)
self.salary = salary

---

<!-- p.164 -->

3.2 单继承背景下的属性查找
3.3 菱形问题
self.level = level
def score(self):
print('老师 %s 正在给学生打分' %self.name)
t = Teacher('agen',25,'man',50000,'一级')
print(t.__dict__) ## {'name': 'agen', 'age': 25, 'sex': 'man', 'salary': 50000,
'level': '一级'}
stu_1 = Student('aini',22,'man')
print(stu_1.name,stu_1.age,stu_1.sex) ## aini 22 man
print(stu_1.school) ## OLDBOY
stu_1.choose_course() ## 学生 aini正在选课
class Foo:
def f1(self):
print('Foo.f1')
def f2(self):
print('Foo.f2')
self.f1() ## z这里如何调用自己的f1函数
# 第一种方法 Foo.f1(self)
# 第二种方法，把f1函数改为次有属性 self.__f1()
class Bar(Foo):
def f1(self):
print('Bar.f1')
obj = Bar()
obj.f2() ## 到父类调f2,也会把自己传进来，随意 self.f1() == obj.f1()
## Foo.f2
## Bar.f1
'''
大多数面向对象语言都不支持多继承，而在Python中，一个子类是可以同时继承多个父类的，这固然可以带来
一个子类可以对多个不同父类加以重用的好处，但也有可能引发著名的 Diamond problem菱形问题(或称钻
石问题，有时候也被称为“死亡钻石”)，菱形其实就是对下面这种继承结构的形象比喻

---

<!-- p.165 -->

3.4 继承原理
3.5 深度优先和广度优先
'''
class A(object):
def test(self):
print('from A')
class B(A):
def test(self):
print('from B')
class C(A):
def test(self):
print('from C')
class D(B,C):
pass
obj = D()
obj.test() # 结果为：from B
## python2 和 Python3 里算出来的mro不一样的
## python到底是如何实现继承的呢？ 对于你定义的每一个类，Python都会计算出一个方法解析顺序(MRO)
列表，该MRO列表就是一个简单的所有基类的线性顺序列表，如下
D.mro()
## [<class '__main__.D'>, <class '__main__.B'>, <class '__main__.C'>, <class
'__main__.A'>, <class 'object'>]
B.mro()
## [<class '__main__.B'>, <class '__main__.A'>, <class 'object'>]
## 1.子类会先于父类被检查
## 2.多个父类会根据它们在列表中的顺序被检查
## 3.如果对下一个类存在两个合法的选择,选择第一个父类
## 参照下述代码，多继承结构为非菱形结构，此时，会按照先找B这一条分支，然后再找C这一条分支，最后
找D这一条分支的顺序直到找到我们想要的属性

---

<!-- p.166 -->

class E:
def test(self):
print('from E')
class F:
def test(self):
print('from F')
class B(E):
def test(self):
print('from B')
class C(F):
def test(self):
print('from C')
class D:
def test(self):
print('from D')
class A(B, C, D):
# def test(self):
# print('from A')
pass
print(A.mro())
'''
[<class '__main__.A'>, <class '__main__.B'>, <class '__main__.E'>, <class
'__main__.C'>, <class '__main__.F'>, <class '__main__.D'>, <class 'object'>]
'''
## 如果继承关系为菱形结构，那么经典类与新式类会有不同MRO，分别对应属性的两种查找方式：深度优先和
广度优先
#################### 这是经典类：深度优先查找
class G: # 在python2中，未继承object的类及其子类，都是经典类
def test(self):
print('from G')

---

<!-- p.167 -->

class E(G):
def test(self):
print('from E')
class F(G):
def test(self):
print('from F')
class B(E):
def test(self):
print('from B')
class C(F):
def test(self):
print('from C')
class D(G):
def test(self):
print('from D')
class A(B,C,D):
# def test(self):
# print('from A')
pass
obj = A()
obj.test() # 如上图，查找顺序为:obj->A->B->E->G->C->F->D->object
# 可依次注释上述类中的方法test来进行验证,注意请在python2.x中进行测试
#################### 这是新式类：广度优先查找
class G(object):
def test(self):
print('from G')
class E(G):
def test(self):
print('from E')
class F(G):
def test(self):
print('from F')

---

<!-- p.168 -->

3.6 Mixins机制（解决多继承问题）
class B(E):
def test(self):
print('from B')
class C(F):
def test(self):
print('from C')
class D(G):
def test(self):
print('from D')
class A(B,C,D):
# def test(self):
# print('from A')
pass
obj = A()
obj.test() # 如上图，查找顺序为:obj->A->B->E->C->F->D->G->object
# 可依次注释上述类中的方法test来进行验证
## Mixins机制核心：多继承背景下，尽可能地提升多继承的可读性
## 让多继承满足人类的思维习惯
## 民航飞机、直升飞机、轿车都是一个（is-a）交通工具，前两者都有一个功能是飞行fly，但是轿车没
有，所以如下所示我们把飞行功能放到交通工具这个父类中是不合理的
class Vehicle: # 交通工具
def fly(self):
'''
飞行功能相应的代码
'''
print("I am flying")
class CivilAircraft(Vehicle): # 民航飞机
pass
class Helicopter(Vehicle): # 直升飞机
pass
class Car(Vehicle): # 汽车并不会飞，但按照上述继承关系，汽车也能飞了
pass
## ------------------------------------------------------------------------------
-------------------------------
## 解决方法
class Vehicle: # 交通工具
pass
class FlyableMixin:
def fly(self):
'''
飞行功能相应的代码
'''
print("I am flying")

---

<!-- p.169 -->

3.7 使用minin注意事项
3.8 派生与方法重用
class CivilAircraft(FlyableMixin, Vehicle): # 民航飞机
pass
class Helicopter(FlyableMixin, Vehicle): # 直升飞机
pass
class Car(Vehicle): # 汽车
pass
# ps: 采用某种规范（如命名规范）来解决具体的问题是python惯用的套路
## ------------------------------------------------------------------------------
-------------------------------
## 使用Minin
class Vehicle: # 交通工具
pass
class FlyableMixin:
def fly(self):
'''
飞行功能相应的代码
'''
print("I am flying")
class CivilAircraft(FlyableMixin, Vehicle): # 民航飞机
pass
class Helicopter(FlyableMixin, Vehicle): # 直升飞机
pass
class Car(Vehicle): # 汽车
pass
# ps: 采用某种规范（如命名规范）来解决具体的问题是python惯用的套路
## ------------------------------------------------------------------------------
--------------------------
## 使用Mixin类实现多重继承要非常小心
## 首先它必须表示某一种功能，而不是某个物品，python 对于mixin类的命名方式一般以 Mixin,
able, ible 为后缀
## 其次它必须责任单一，如果有多个功能，那就写多个Mixin类，一个类可以继承多个Mixin，为了保证遵
循继承的“is-a”原则，只能继承一个 标识其归属含义的父类
## 然后，它不依赖于子类的实现
## 最后，子类即便没有继承这个Mixin类，也照样可以工作，就是缺少了某个功能。（比如飞机照样可以载
客，就是不能飞了）
# 子类可以派生出自己新的属性，在进行属性查找时，子类中的属性名会优先于父类被查找，例如每个老师还
有职称这一属性，我们就需要在Teacher类中定义该类自己的__init__覆盖父类的
class OldBoyPeople:
def __init__(self,name,age,sex):
self.name = name

---

<!-- p.170 -->

3.9 组合
self.age = age
self.sex = sex
def f1(self):
print('%s say hello' %self.name)
class Teacher(OldBoyPeople):
def __int__(self,name,age,sex,level,salary):
## 第一种方法（不依赖于继承）
## OldBoyPeople.__init__(self,name,age,sex)
## 第二种方法（严格依赖继承,只能用于新式类）
## Python2中需要传入类和本身
## super(Teacher, self).__init__(name.age, sex)
## Python3中什么也不需要传
super().__init__(name,age,sex)
## super 根据当前类的mro去访问父类里面去找
self.level = level
self.salary = salary
## super 严格遵守 mor 去找父类，而不是我们肉眼看到的
#A没有继承B
class A:
def test(self):
super().test()
class B:
def test(self):
print('from B')
class C(A,B):
pass
C.mro() # 在代码层面A并不是B的子类，但从MRO列表来看，属性查找时，就是按照顺序C->A->B-
>object，B就相当于A的“父类”
## [<class '__main__.C'>, <class '__main__.A'>, <class '__main__.B'>,<class
‘object'>]
obj=C()
obj.test() # 属性查找的发起者是类C的对象obj，所以中途发生的属性查找都是参照C.mro()
## from B
'''
在一个类中以另外一个类的对象作为数据属性，称为类的组合。组合与继承都是用来解决代码的重用性问题。
不同的是：继承是一种“是”的关系，比如老师是人、学生是人，当类之间有很多相同的之处，应该使用继承；
而组合则是一种“有”的关系，比如老师有生日，老师有多门课程，当类之间有显著不同，并且较小的类是较大
的类所需要的组件时，应该使用组合，如下示例
'''
class Course:
def __init__(self,name,period,price):
self.name=name

---

<!-- p.171 -->

4，多态
4.1 多态的一种方式
self.period=period
self.price=price
def tell_info(self):
print('<%s %s %s>' %(self.name,self.period,self.price))
class Date:
def __init__(self,year,mon,day):
self.year=year
self.mon=mon
self.day=day
def tell_birth(self):
print('<%s-%s-%s>' %(self.year,self.mon,self.day))
class People:
school='清华大学'
def __init__(self,name,sex,age):
self.name=name
self.sex=sex
self.age=age
#Teacher类基于继承来重用People的代码，基于组合来重用Date类和Course类的代码
class Teacher(People): #老师是人
def __init__(self,name,sex,age,title,year,mon,day):
super().__init__(name,age,sex)
self.birth=Date(year,mon,day) #老师有生日
self.courses=[] #老师有课程，可以在实例化后，往该列表中添加Course类的对象
def teach(self):
print('%s is teaching' %self.name)
python=Course('python','3mons',3000.0)
linux=Course('linux','5mons',5000.0)
teacher1=Teacher('lili','female',28,'博士生导师',1990,3,23)
# teacher1有两门课程
teacher1.courses.append(python)
teacher1.courses.append(linux)
# 重用Date类的功能
teacher1.birth.tell_birth()
# 重用Course类的功能
for obj in teacher1.courses:
obj.tell_info()
## 多态：同一种事务的多种状态
## 多态性指的是可以在不考虑对象具体类型的情况下而直接使用对象
class Animal:
def say(self):
print('动物基本的发声')

---

<!-- p.172 -->

4.2 Python推崇的多态
class Person(Animal):
def say(self):
super().say()
print('啊啊啊啊啊啊啊啊')
class Dog(Animal):
def say(self):
super().say()
print('汪汪汪')
class Pig(Animal):
def say(self):
super().say()
print('哼哼哼')
person = Person()
dog = Dog()
pig = Pig()
## 定义统一的接口，实现多态
def animal_say(animal):
animal.say()
animal_say(person)
animal_say(dog)
animal_say(pig)
## 多态的例子
def my_len(val):
return val.__len__()
my_len('aini')
my_len([1,12,3,4,5,'hhh'])
my_len({'name':'aini','age':22})
## 鸭子类型，不用继承
class Cpu:
def read(self):
print('cpu read')
def write(self):
print('cpu write')
class Meu:
def read(self):
print('meu read')
def write(self):
print('meu write')
class Txt:
def read(self):
print('txt read')

---

<!-- p.173 -->

5，classmethod
6，staticmethod
7，内置方法
def write(self):
print('txt write')
cpu = Cpu()
meu = Meu()
txt = Txt()
import setting
class Mysql:
def __init__(self,ip,port):
self.ip = ip
self.port = port
def func(self):
print('%s %s' %(self.ip,self.port))
@classmethod ## 提供一种初始化对象的方法
def from_conf(cls):
return cls(setting.IP,setting.PORT) ## 返回的就是一个实例化的对象，不需要我自
己一个个创建
obj = Mysql.from_conf()
print(obj.__dict__) ## {'ip': '127.0.0.1', 'port': 3306}
class Mysql:
def __init__(self,ip,port):
self.ip = ip
self.port = port
@staticmethod
def create_id():
import uuid
return uuid.uuid4()
obj = Mysql('127.0.0.1','3306')
## 像普通函数一样调用就可以，不会自动传参，需要人工传参
print(Mysql.create_id()) ## 57c42038-b169-4f25-9057-d83795d097cc
print(obj.create_id()) ## 485372bc-efca-4da8-a446-b11c7bbf3c9b

---

<!-- p.174 -->

7.1 什么是内置方法
7.2 如何使用内置方法
## 定义在类内部，以__开头和__结尾的方法称之为内置方法
## 会在满足某种情况下回自动触发执行
## 为什么用： 为了定制化我们的类或者对象
# __str__
# __del__
class People:
def __init__(self,name,age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>'%(self.name,self.age))
obj = People('aini',22)
print(obj) ## <__main__.People object at 0x00000276F6B8B730>
## ----------------------------------------------------------------------
## __str__ 来完成定制化操作
class People:
def __init__(self,name,age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>'%(self.name,self.age))
def __str__(self):
print('这是xxxxx对象') ## 值起到提示作用
return '<%s:%s>' % (self.name, self.age) ## 必须要有return，而且返回字符串
obj = People('aini',22)
print(obj) ## <aini:22>
## ------------------------------------------------------------------------------
----------
# __del__ :在清理对象时触发，会先执行该方法
class People:
def __init__(self,name,age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>'%(self.name,self.age))
def __del__(self):
print('running......')

---

<!-- p.175 -->

8,元类介绍
obj = People('aini',22)
print('=======================')
'''
== == == == == == == == == == == = ## 程序运行完了，要清理对象
running...... ## 清理对象时云运行
'''
## ------------------------------------------------------------------------------
---------
class People:
def __init__(self,name,age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>'%(self.name,self.age))
def __del__(self):
print('running......')
obj = People('aini',22)
del obj
print('=======================')
'''
running...... ## 清理对象时云运行
== == == == == == == == == == == = ## 程序运行完了
'''
## ------------------------------------------------------------------------------
---------------
##### 对象本身占得是应用程序的内存空间，所以没有多大用处
##### 但是如果对象某个属性x 比如 obj.x 占得是操作系统内存空间，对象运行完了以后Python回收的是
程序中的内存空间
### 操作系统不会被回收
class People:
def __init__(self,name,age):
self.name = name
self.age = age
self.x = open('aini.txt','w',encoding="utf-8")
def say(self):
print('<%s:%s>'%(self.name,self.age))
def __del__(self):
print('running......')
## 发起系统调用，告诉系统回收操作系统资源,比如如下：
self.x.close()
obj = People('aini',22)
print('=======================')

---

<!-- p.176 -->

8.1 class关键字创建类的步骤
## 元类----------------> 用来实例化产生类的那个类
## 关系 ： 元类---------------实例化 --------------->类----------------------> 对象
class People:
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
## 查看内置元类
print(type(People)) # <class 'type'>
print(type(int)) # <class 'type'>
## class关键字定义的类和内置的类都是由type产生的
# 类三大特征：类名 class_name || 类的基类 clas_bases = (Object) || 类体本身 --> 一对字
符串（执行类体代码，拿到运行空间）
class People:
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
class_body = '''
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
'''
class_dic = {} # 定义类的命名空间
# 类名
class_name = "People"
# 类的基类
clas_bases = (object,)
# 执行类体代码，拿到运行空间
exec(class_body,{},class_dic) # 空字典指的是全局命名空间 class_dic是类的命名空间
## 运行拿到exec以后可以拿到类体代码的运行空间，放在class_dic 里
print(class_dic)
## {'__init__': <function __init__ at 0x0000016A0BDC9900>, 'say': <function
say at 0x0000016A0BE2E320>}
# 调用元类
People = type(class_name,class_basis,class_dic)
print(People) ## <class '__main__.People'>

---

<!-- p.177 -->

8.2 定制元类，控制类的产生
## 定制元类
class Mymeta(type): ## 只有继承了type类的类才可以称之为元
## 运行__init__方法的时候，空对象和这些class_name,class_basis,class_dic一共四个参数
一起传进来了
## 所以需要四个参数接受
## 重写了造对象的方法，不写__new__方法的话自动创建空对象
## 参数为： 类本身，调用类时所传入的参数
def __new__(xls,*args,**kwargs):
##第一种方法 ----------------> 调父类的__new__()方法造对象
return super().__new__(cls,*args,**kwargs)
## 第二种方法 -----------------> 调用元类的内置方法
return type.__new__(cls,*args,**kwargs)
## 可以控制类的产生
def __init__(self,class_name,class_basis,class_dic):
## 类的首字母大写
if not x.capitalize():
raise NameError('类名的首字母必须大写啊！！！！')
class People(object ,metaclass = Mymeta):
# class产生类的话会自动继承object
# 底层的话需要明确之指定继承object类
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
class_body = '''
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
'''
class_dic = {} # 定义类的命名空间
# 类名
class_name = "People"
# 类的基类
clas_bases = (object,)
# 执行类体代码，拿到运行空间
exec(class_body,{},class_dic)
# 调用元类
People = Mymeta(class_name,class_basis,class_dic) ## 调用 type.__call__(方法)
## 将参数先传给 __new__方法，造空对象
## 然后参数传递给 __init__方法初始化类
## 调用Mymeta发生的事儿,调用Mymeta 就是type.__call__()
# 先造一个空对象 ==> People 调用__new__方法

---

<!-- p.178 -->

8.3 new(方法)
8.4 call（方法）
# 调用Mymeta这个类的__inti__方法，完成初始化对象的操作(这个过程中可以控制类的产生)
# 返回初始化好的对象
## 总结
# 控制造空对象过程 重写 __new__()方法
# 控制类的产生 重写 __init__()方法
## 具体看 8.2 控制造空对象的过程
## __new__() 放下造对象时，早于 __init__() 方法运行
## 8.1 中
# 调用元类时
People = Mymeta(class_name,class_basis,class_dic) ## 本质就是调用 type的
__call__()方法
class Foo:
def __init__(self,x,y):
self.x = x
self.y = y
def __call__(self,name,age):
print(name,age)
print('我运行了obj下面的__call__方法')
obj = Foo(111,222)
obj("aini",'22')
# 'aini' 22
# '我运行了obj下面的__call__方法'
## 对象的类里定义__call__方法的话，实例对象可以调用
### -------------------------------------------------------------------
## 如果想要控制类的调用， 那就重写__call__()方法
## 定制元类
class Mymeta(type):
def __call__(self,*args,**kwargs):
## Mymeta.__call__函数内会调用People.__new__()方法
people_obj = self__new__(self)
## 可以对类进行定制化
obj.__dict__['xxxx'] ='所有的obj产生的类我新加了一个属性'
## Mymeta.__call__函数内调用People.__inti__()方法
self.__init__(people_obj,*args,**kwargs)
## 重写了造对象的方法，不写__new__方法的话自动创建空对象
## 参数为： 类本身，调用类时所传入的参数
def __new__(xls,*args,**kwargs):
##第一种方法 ----------------> 调父类的__new__()方法造对象
return super().__new__(cls,*args,**kwargs)
## 第二种方法 -----------------> 调用元类的内置方法
return type.__new__(cls,*args,**kwargs)

---

<!-- p.179 -->

## 可以控制类的产生
def __init__(self,class_name,class_basis,class_dic):
## 类的首字母大写
if not x.capitalize():
raise NameError('类名的首字母必须大写啊！！！！')
class People(object ,metaclass = Mymeta):
# class产生类的话会自动继承object
# 底层的话需要明确之指定继承object类
def __init__(self, name, age):
self.name = name
self.age = age
def __new__(cls,*args,**kwargs):
# 造对象
return object.__new__(cls,*args,**kwargs)
def say(self):
print('<%s:%s>' % (self.name, self.age))
## ------------------------------------------------------------
class_body = '''
def __init__(self, name, age):
self.name = name
self.age = age
def say(self):
print('<%s:%s>' % (self.name, self.age))
'''
class_dic = {} # 定义类的命名空间
class_name = "People"
clas_bases = (object,)
exec(class_body,{},class_dic)
People = Mymeta(class_name,class_basis,class_dic) ## 调用 type.__call__(方法)
## 调用Mymeta发生的事儿,调用Mymeta 就是type.__call__()
# 先造一个空对象 ==> People 调用__new__方法
# 调用Mymeta这个类的__inti__方法，完成初始化对象的操作(这个过程中可以控制类的产生)
# 返回初始化好的对象
obj = People('aini',22)
# 实例化People发生的三件事
# 调用Mymeta.__call__(self,*args,**kwargs)方法
# Mymeta.__call__函数内会调用People.__new__()方法
# Mymeta.__call__函数内调用People.__inti__()方法

---

<!-- p.180 -->

8.5 属性查找的原则
六，网络编程
10.1 cs架构与bs架构
10.2 网络通信
10.3 OSI七层协议
10.4 网络协议
## 属性查找的原则：对象 ----> 类 ----------->父类
## 切记：父类不是元类，不会去从元类里找
## cs架构
## Client ----------------------------------------- Server
# 客服端软件 <==============================> 服务端软件
# 操作系统<===================================> 操作系统
# 计算机硬件 <================================> 计算机硬件
## bs架构
## Brower ----------------------------------------------- Server
## 网络存在的意义就是跨地域数据传输---------》 称之为通信
## 网络 = 物理链接介质 + 互联网通信协议
## 五层协议
# 应用层
# 传输层
# 网络层
# 数据链路层
# 物理层
## 协议：规定数据的组织格式 格式：头部 + 数据部分

---

<!-- p.181 -->

10.4.1 物理层
10.4.2 数据链路层（帧）
## 计算机1 ----------------------------计算机2、
## 应用层 ------------------------------应用层
## 传输层 ----------------------------- 传输层
## 网络层 ----------------------------- 网络层 ------> (源IP地址，目标IP地址) 数据1
## 数据链路层 --------------------------数据链路层 --->(源mac地址，目标mac地址) 数据
2((源IP地址，目标IP地址) 数据1)
## 物理层1 ------------二层交互机------------物理层2
# 二层交互机将从 物理层1接受的 二进制数据接收到以后可以解析到数据链路层(源mac地址，目标mac地
址) 数据2 再转换成二进制 发给物理层2
## 物理层由来：上面提到，孤立的计算机之间要想一起玩，就必须接入internet，言外之意就是计算机之间
必须完成组网
## 物理层功能：主要是基于电器特性发送高低电压(电信号)，高电压对应数字1，低电压对应数字0
## 物理层负责发送电信号
## 单纯的电信号毫无意义，必须对其进行分组
## 数据链路层： Ethernet以太网协议
## 规定一：一组数据称之为一个数据帧
## 规定二：数据帧分成两部分 头 + 数据两部分
## 头: 源地址与目标地址，该地址是Mac地址
## 数据：包含的是网络层整体的内容
## 规定三：但凡介入互联网的主机，必须有网卡，每一块网卡在出场时标志好一个全世界独一无二的地
址该地址称之为-----> mac地址
## mac地址：(了解)
'''
head中包含的源和目标地址由来：ethernet规定接入internet的设备都必须具备网卡，发送端和接收
端的地址便是指网卡的地址，即mac地址
mac地址：每块网卡出厂时都被烧制上一个世界唯一的mac地址，长度为48位2进制，通常由12位16进制
数表示（前六位是厂商编号，后六位是流水线号）
'''
## head包含：(固定18个字节) ----------------- 源地址与目标地址，该地址是Mac地址
'''
发送者／源地址，6个字节
接收者／目标地址，6个字节

---

<!-- p.182 -->

10.4.3 网络层（包）
3-1 ip协议
数据类型，6个字节
data包含：(最短46字节，最长1500字节)
'''
## 数据包的具体内容
## head长度＋data长度＝最短64字节，最长1518字节，超过最大限制就分片发送
## 注意：计算机通信基本靠吼，既以太网协议的工作方式是广播
## 网络层：IP协议
## 划分IP协议
## 每一个广播域但凡要接通外部，一定要有一个网关帮内部的计算机转发包到公网网关与外界通信走的
是路由协议
## 规定1：一组数据称之为一个数据包
## 规定2： 数据帧分成两个部分----> 头 + 数据
## 头包含：源地址与目标地址，该地址是IP地址
## 数据包含：传输层整体的内容
# IP协议：
'''
1,规定网络地址的协议叫ip协议，它定义的地址称之为ip地址，广泛采用的v4版本即ipv4，它规
定网络地址由32位2进制表示
2,范围0.0.0.0-255.255.255.255
3,一个ip地址通常写成四段十进制数，例：172.16.10.1

---

<!-- p.183 -->

3-2 子网掩码
'''
## ip地址分成两部分
# 网络部分：标识子网
# 主机部分：标识主机
# 注意：单纯的ip地址段只是标识了ip地址的种类，从网络部分或主机部分都无法辨识一个ip所处的子
网
# 例：172.16.10.1与172.16.10.2并不能确定二者处于同一子网
#ipv4地址：
# 8bit.8bit.8bit.8bit
0.0.0.0 ~ 255.255.255.255
## ipv6
## 目前在逐渐普及
## 子网掩码
# 8bit.8bit.8bit.8bit
## 一个合法的IPv4地址组成部分=ip地址/子网掩码 ---------------------> 区分广播域
## 172.16.10.1/255.255.255.0
## ## 172.16.10.1/24 -----------------> 表示24位二进制数
'''
知道”子网掩码”，我们就能判断，任意两个IP地址是否处在同一个子网络。方法是将两个IP地址与子网
掩码分别进行AND运算（两个数位都 为1，运算结果为1，否则为0），然后比较结果是否相同，如果是的
话，就表明它们在同一个子网络中，否则就不是。
'''
## 同为1结果为1，有0结果为0
## 计算机1的
## IP地址
172.16.10.1： 10101100.00010000.00001010.000000001
## 子网掩码地址
255255.255.255.0: 11111111.11111111.11111111.00000000
## 网络地址
10110101100.00010000.00001010.000000001-
>172.16.10.0
## 计算机2的
## IP地址
172.16.10.2： 10101100.00010000.00001010.000000010
## 子网掩码地址
255255.255.255.0: 11111111.11111111.11111111.00000000
## 网络地址
10101100.00010000.00001010.000000001-
>172.16.10.0
## 两个计算机网络地址一样，所以属于一个局域网内

---

<!-- p.184 -->

3-3 APR协议
3-4 总结性知识
## 事先知道的是对方的IP地址
## 但是计算机的底层通信是基于ethernet以太网协议的mac地址通信
##API协议 -----------> 能够将IP地址解析成mac地址
## 两台计算机再同一个局域网内，直接发包就可以
计算计1 直接 计算机2
ARP：
自己的IP，对方的IP
#-1 计算二者的网络地址，如果一样，那ARP协议拿到计算机2的mac地址就可以
#-2 发送广播包
## 两台计算机不在同一个局域网内
计算计1 网关 计算机2
ARP：
自己的IP，对方的IP
# 计算二者的网络地址，如果不一样，应该拿到网关的mac地址
## FF:FF:FF:FF:FF:FF ---------------------->意思就是要对方的Mac地址
##-1 如果在同一个局域网内，那就拿到了对方的Mac地址
##-2 发送广播包
## Mac地址标识的是局域网内的一台机器
## IP地址 + Mac地址 -------------------> 可以标识全世界范围内独一无二的一台计算机
## IP+ Mac + port -----------------------> 可以找到全世界范围内独一无二的应用程序
## 或者
## IP地址 ----------> 可以标识全世界范围内独一无二的一台计算机
##

---

<!-- p.185 -->

10.4.4 传输层（段）
4-1 tcp协议
## 传输层功能：建立端口到端口的通信
## 补充：端口范围0-65535，0-1023为系统占用端口
## 自定义协议需要注意的问题：
#-1 两大组成部分= 头部 + 数据部分
# 头部:放对数据的描述信息
# 比如：数据要发给谁，数据的类型，数据的长度
# 数据部分：想要发的数据
#-2 头部的长度必须固定
# 因为接受端要通过头部获取所接收数据的详细信息
# Ethernet头 + IP头 + TCP头 + 应用层的头 + 应用层数据
## TCP头部：源端口，目标端口，....... （20字节）
## TCP协议工作方式：建立一个双向通信的链接
C -------------------------------> S 客户端向服务端发数据
C <-------------------------------> S 服务端向客户端发请求
## 三次握手建立链接------------为传数据做准备
C S
| -------------------------------------> | 第一次：发起跟服务端的链接请求
| |
|<---------------------------------------| 第二次：同意客户端的请求，并向客户端发
链接请求
| |
|--------------------------------------->| 第三次：同意服务端同意
| |
## 四次握手断开链接-----------------由于断开链接时，由于链接内有数据传输，所以必须分四次断开

---

<!-- p.186 -->

4-2 UDP协议
10 -------- scoket 抽象层(套接字)
10.4.5 应用层
## tcp 发数据是可靠的（效率不高) ---------> 因为客户端发数据给服务端，服务端有个确认信息，客
户端才会把内存数据清理掉
## 若果客户端发数据到服务端，服务端没回应，客户端会重发一份给服务端，反过来也是
## 发送数据必须等到对方确认后才算完成，才会将自己内存中的数据清理掉
## 当服务端大量处于TIME_WAIT状态时意味着服务端正在经历高并发
## 为了提高传输效率，可以使用UDP协议，发数据不需要确认，发完就清理数据，不需要对方确认--------
------但是不可靠
## 应用层由来：用户使用的都是应用程序，均工作于应用层，互联网是开发的，大家都可以开发自己的应用
程序，数据多种多样，必须规定好数据的组织形式
## 应用层功能：规定应用程序的数据格式。
## 例：TCP协议可以为各种各样的程序传递数据，比如Email、WWW、FTP等等。那么，必须有不同协议规定
电子邮件、网页、FTP数据的格式，这些应用程序协议就构成了”应用层”。

---

<!-- p.187 -->

10.4.6 总结
10.5 网络通信实现
## 想实现网络通信，每台主机需具备四要素
## 本机的IP地址
## 子网掩码
## 网关的IP地址
## DNS的IP地址
## 获取这四要素分两种方式

---

<!-- p.188 -->

10.5.1 DHCP协议(计算机获取自己的IP，子网掩码等等信息)
10.5.2 DNS域名解析
#获取这四要素分两种方式
# 1.静态获取
# 即手动配置
# 2.动态获取
#通过dhcp获取
#（1）最前面的”以太网标头”，设置发出方（本机）的MAC地址和接收方（DHCP服务器）的MAC地址。前者就
是本机网卡的MAC地址，后者这时不知道，就填入一个广播地址：FF-FF-FF-FF-FF-FF。
#（2）后面的”IP标头”，设置发出方的IP地址和接收方的IP地址。这时，对于这两者，本机都不知道。于
是，发出方的IP地址就设为0.0.0.0，接收方的IP地址设为255.255.255.255。
#（3）最后的”UDP标头”，设置发出方的端口和接收方的端口。这一部分是DHCP协议规定好的，发出方是68
端口，接收方是67端口。
# 这个数据包构造完成后，就可以发出了。以太网是广播发送，同一个子网络的每台计算机都收到了这个包。
因为接收方的MAC地址是FF-FF-FF-FF-FF-FF，看不出是发给谁的，所以每台收到这个包的计算机，还必须
分析这个包的IP地址，才能确定是不是发给自己的。当看到发出方IP地址是0.0.0.0，接收方是
255.255.255.255，于是DHCP服务器知道”这个包是发给我的”，而其他计算机就可以丢弃这个包。
# 接下来，DHCP服务器读出这个包的数据内容，分配好IP地址，发送回去一个”DHCP响应”数据包。这个响应
包的结构也是类似的，以太网标头的MAC地址是双方的网卡地址，IP标头的IP地址是DHCP服务器的IP地址
（发出方）和255.255.255.255（接收方），UDP标头的端口是67（发出方）和68（接收方），分配给请求
端的IP地址和本网络的具体参数则包含在Data部分。
# 新加入的计算机收到这个响应包，于是就知道了自己的IP地址、子网掩码、网关地址、DNS服务器等等参数
# DNS的作用：在互联网中，其实没有类似于www.xxx.com这种域名方式，而替代的是以IP地址，如
222.222.222.222，那我们在IE地址栏中应当输入222.222.222.222才能打开网站www.xxx.com，但我
们细想一下，互联网上的网站成千上万，如果每个网站登陆都需要记住一大串数字，那是不是特别不方便，对
于记忆力不强的人，根本无法记住这么烦琐的数字。这个时候DNS就出现了，它的作用就是将
222.222.222.222解析为www.xxx.com，那么我们登陆的时候就直接输入域名就可以了。
# 为什么一定要设置DNS才能上网？有些朋友可能会发现，为什么我可能登陆QQ、MSN，但却打不开网页呢？
其实大部分原因都是因为DNS服务器故障造成的，DNS服务器地址是唯一的，是运营商提供给终端用户用来解析
IP地址及域名的关系，而如果不设定DNS服务器地址，那么就无法查询地址的去向，自然也就打不开网页，而
QQ、MSN等即时聊天软件，采用的是UDP传输协议，即不可靠传输协议，无需提供DNS服务器地址，也同样可以
登陆。
## DNS 查询域名用 UDP协议

---

<!-- p.189 -->

10.5.3 dns的两种查询方式
#一 ：递归
##主机向本地域名服务器的查询一般都是采用递归查询。所谓递归查询就是：如果主机所询问的本地域名服务
器不知道被查询的域名的IP地址，那么本地域名服务器就以DNS客户的身份，向其它根域名服务器继续发出查
询请求报文(即替主机继续查询)，而不是让主机自己进行下一步查询。因此，递归查询返回的查询结果或者是
所要查询的IP地址，或者是报错，表示无法查询到所需的IP地址。
# 二：迭代
## 本地域名服务器向根域名服务器的查询的迭代查询。迭代查询的特点：当根域名服务器收到本地域名服务
器发出的迭代查询请求报文时，要么给出所要查询的IP地址，要么告诉本地服务器：“你下一步应当向哪一个
域名服务器进行查询”。然后让本地服务器进行后续的查询。根域名服务器通常是把自己知道的顶级域名服务器
的IP地址告诉本地域名服务器，让本地域名服务器再向顶级域名服务器查询。顶级域名服务器在收到本地域名
服务器的查询请求后，要么给出所要查询的IP地址，要么告诉本地服务器下一步应当向哪一个权限域名服务器
进行查询。最后，知道了所要解析的IP地址或报错，然后把这个结果返回给发起查询的主机。

---

<!-- p.190 -->

10.5.4 域名解析例子
#下面举一个例子演示整个查询过程：
'''
假定域名为m.xyz.com的主机想知道另一个主机y.abc.com的IP地址。例如，主机m.xyz.com打算发送邮
件给y.abc.com。这时就必须知道主机y.abc.com的IP地址。下面是图2的几个查询步骤：
1、主机m.abc.com先向本地服务器dns.xyz.com进行递归查询。
2、本地服务器采用迭代查询。它先向一个根域名服务器查询。
3、根域名服务器告诉本地服务器，下一次应查询的顶级域名服务器dns.com的IP地址。
4、本地域名服务器向顶级域名服务器dns.com进行查询。
5、顶级域名服务器dns.com告诉本地域名服务器，下一步应查询的权限服务器dns.abc.com的IP
地址。
6、本地域名服务器向权限域名服务器dns.abc.com进行查询。
7、权限域名服务器dns.abc.com告诉本地域名服务器，所查询的主机的IP地址。
8、本地域名服务器最后把查询结果告诉m.xyz.com。
# 整个查询过程共用到了8个UDP报文。
为了提高DNS查询效率，并减轻服务器的负荷和减少因特网上的DNS查询报文数量，在域名服务器中
广泛使用了高速缓存，用来存放最近查询过的域名以及从何处获得域名映射信息的记录。
例如，在上面的查询过程中，如果在m.xyz.com的主机上不久前已经有用户查询过y.abc.com的
IP地址，那么本地域名服务器就不必向根域名服务器重新查询y.abc.com的IP地址，而是直接把告诉缓存中
存放的上次查询结果(即y.abc.com的IP地址)告诉用户。
由于名字到地址的绑定并不经常改变，为保持告诉缓存中的内容正确，域名服务器应为每项内容设
置计时器并处理超过合理时间的项(例如每个项目两天)。当域名服务器已从缓存中删去某项信息后又被请求查
询该项信息，就必须重新到授权管理该项的域名服务器绑定信息。当权限服务器回答一个查询请求时，在响应
中都指明绑定有效存在的时间值。增加此时间值可减少网络开销，而减少此时间值可提高域名解析的正确性。
不仅在本地域名服务器中需要高速缓存，在主机中也需要。许多主机在启动时从本地服务器下载名
字和地址的全部数据库，维护存放自己最近使用的域名的高速缓存，并且只在从缓存中找不到名字时才使用域
名服务器。维护本地域名服务器数据库的主机应当定期地检查域名服务器以获取新的映射信息，而且主机必须
从缓存中删除无效的项。由于域名改动并不频繁，大多数网点不需花精力就能维护数据库的一致性。
'''

---

<!-- p.191 -->

10.5.5 DNS解析流程举例
'''
如上图所示，我们将详细阐述DNS解析流程。
1、首先客户端位置是一台电脑或手机，在打开浏览器以后，比如输入http://www.zdns.cn的域名，它首先
是由浏览器发起一个DNS解析请求，
如果本地缓存服务器中找不到结果，则首先会向根服务器查询，根服务器里面记录的都是各个顶级域所在的服
务器的位置，当向根请求http://www.zdns.cn的时候，
根服务器就会返回.cn服务器的位置信息。
2、递归服务器拿到.cn的权威服务器地址以后，就会寻问cn的权威服务器，知不知道http://www.zdns.cn
的位置。这个时候cn权威服务器查找并返回http://zdns.cn服务器的地址。
3、继续向http://zdns.cn的权威服务器去查询这个地址，由http://zdns.cn的服务器给出了地址：
202.173.11.10

---

<!-- p.192 -->

10.5.6 DNS缓存及分类
10.5.7 浏览器DNS查找顺序
4、最终才能进行http的链接，顺利访问网站。
5、这里补充说明，一旦递归服务器拿到解析记录以后，就会在本地进行缓存，如果下次客户端再请求本地的递
归域名服务器相同域名的时候，就不会再这样一层一层查了，
因为本地服务器里面已经有缓存了，这个时候就直接把http://www.zdns.cn的A记录返回给客户端就可以
了。
'''
# DNS缓存指DNS返回了正确的IP之后，系统就会将这个结果临时储存起来。并且它会为缓存设定一个失效时
间 (例如N小时)，在这N小时之内，当你再次访问这个网站时，系统就会直接从你电脑本地的DNS缓存中把结
果交还给你，而不必再去询问DNS服务器，变相“加速”了网址的解析。
# 当然，在超过N小时之后，系统会自动再次去询问DNS服务器获得新的结果。所以，当你修改了 DNS 服务
器，并且不希望电脑继续使用之前的DNS缓存时，就需要手动去清除本地的缓存了。
## 分类
'''
1）浏览器DNS缓存（内存中): 浏览器会按照一定频率缓存DNS记录
2）本地操作系统DNS缓存(内存中): 如果浏览器缓存中找不到需要的DNS记录，那就去操作系统找。
3）本地HOSTS文件（硬盘中）: Windows系统中位于C:\Windows\System32\drivers\etc
4）路由器指定的DNS(远程): 路由器自动获取DNS地址，也可以手动修改-登录后台设置DNS服务器地址
ps：路由器DNS被篡改会造成域名劫持，你访问的网址都会被定位到同一个位置，但是IP直接可以访问
5）ISP的DNS服务器（远程）: ISP(Internet Service Provider互联网服务提供商、联通电信移
动)，ISP有专门的DNS服务器应 对DNS查询请求
6）根服务器（远程，跨国）: ISP的DNS服务器还找不到的话，它就会向根服务器发出查询请求
'''
## 浏览器DNS缓存->本地系统DNS缓存->本地计算机HOSTS文件->ISP DNS缓存->递归or迭代搜索
## 期间如果查询到了，也就直接访问ip地址了，这个就像三级缓存原理一样，例如，能够在hosts文件中找
到就不会再去查其他的

---

<!-- p.193 -->

10.5.8 清除DNS缓存
10.6 网络通信流程
##打开cmd执行命令：ipconfig /all
## 全国通用DNS地址（国内用户推荐使用，速度较快！）
## 首先DNS服务器地址添：114.114.114.114 (位于北京人民英雄纪念碑）
## 全球通用DNS地址（此DNS地址为谷歌服务器的）
## 首选DNS服务器地址添：8.8.8.8
## 备用DNS服务器地址添：8.8.4.4
# 查看本地dns缓存命令：ipconfig /displaydns
# 清除本地dns缓存命令：ipconfig /flushdns
# 清除浏览器缓存：
# 我们在开发的时候，有时候会给某个域名绑hosts，用于本地开发测试，但是绑了之后，用谷歌浏览器
访问会发现并没有生效，按F12会 发现访问的还是线上的ip，说明浏览器是有该域名的dns缓存的，
那么如何清除浏览器的dns缓存呢？
# 1、针对谷歌浏览器
#谷歌浏览器清除方法如下：打开浏览器，访问如下地址 chrome://net-internals/#dns
# 点击 clear host cache，就清楚了浏览器的dns缓存，再访问绑hosts的域名，就会发现ip变啦
# 2、针对火狐浏览器
# 如果是firefox火狐浏览器的话，可以按照以下方式：
# 在地址栏中 about:config 并回车，可能会出现一个警告信息，直接点击按钮进入，会出现
firefox的所有配置信息，通过搜索dns 进 行过滤，
# 可以看到一项名为 network.dnsCacheExpirationGracePeriod 项，它对应的值就是DNS缓存
的时间，双击此项，会出现修改的提示 框，填入 0
## 1.本机获取
## 本机的IP地址：192.168.1.100
## 子网掩码：255.255.255.0
## 网关的IP地址：192.168.1.1
## DNS的IP地址：8.8.8.8
## 2.打开浏览器，想要访问Google，在地址栏输入了网址：www.google.com。
## 3.dns协议(基于udp协议)
## 4.HTTP部分的内容，类似于下面这样：
'''
GET / HTTP/1.1
Host: www.google.com
Connection: keep-alive
User-Agent: Mozilla/5.0 (Windows NT 6.1) ……
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Encoding: gzip,deflate,sdch
Accept-Language: zh-CN,zh;q=0.8
Accept-Charset: GBK,utf-8;q=0.7,*;q=0.3
Cookie: … …

---

<!-- p.194 -->

'''
## 5 TCP协议
## TCP数据包需要设置端口，接收方（Google）的HTTP端口默认是80，发送方（本机）的端口是
一个随机生成的1024-65535之间的 整数，假定为51775。
## TCP数据包的标头长度为20字节，加上嵌入HTTP的数据包，总长度变为4980字节。
## 6 IP协议
## 然后，TCP数据包再嵌入IP数据包。IP数据包需要设置双方的IP地址，这是已知的，发送方是
192.168.1.100（本机），接收方是 172.194.72.105（Google）。
# IP数据包的标头长度为20字节，加上嵌入的TCP数据包，总长度变为5000字节。
## 7 以太网协议
'''
最后，IP数据包嵌入以太网数据包。以太网数据包需要设置双方的MAC地址，发送方为本机的网卡MAC地址，
接收方为网关192.168.1.1的MAC地址（通过ARP协议得到）。
以太网数据包的数据部分，最大长度为1500字节，而现在的IP数据包长度为5000字节。因此，IP数据包必须
分割成四个包。因为每个包都有自己的IP标头（20字节），所以四个包的IP数据包的长度分别为1500、
1500、1500、560。
'''
## 8 服务器端响应
'''
经过多个网关的转发，Google的服务器172.194.72.105，收到了这四个以太网数据包。
根据IP标头的序号，Google将四个包拼起来，取出完整的TCP数据包，然后读出里面的”HTTP请求”，接着做
出”HTTP响应”，再用TCP协议发回来。
本机收到HTTP响应以后，就可以将网页显示出来，完成一次网络通信。
'''

---

<!-- p.195 -->

10.7 socket
10.7.1 套接字是什么
10.7.2 套接字工作流程
10.7.3 socket()模块函数用法
## Socket是应用层与TCP/IP协议族通信的中间软件抽象层，它是一组接口。在设计模式中，Socket其实就
是一个门面模式，它把复杂的TCP/IP协议族隐藏在Socket接口后面，对用户来说，一组简单的接口就是全
部，让Socket去组织数据，以符合指定的协议。
## 所以，我们无需深入理解tcp/udp协议，socket已经为我们封装好了，我们只需要遵循socket的规定去
编程，写出的程序自然就是遵循tcp/udp标准的。
## 也有人将socket说成ip+port，ip是用来标识互联网中的一台主机的位置，而port是用来标识这台机器
上的一个应用程序，ip地址是配置到网卡上的，而port是应用程序开启的，ip与port的绑定就标识了互联网
中独一无二的一个应用程序
## 而程序的pid是同一台机器上不同进程或者线程的标识
'''
一个生活中的场景。你要打电话给一个朋友，先拨号，朋友听到电话铃声后提起电话，这时你和你的朋友就建
立起了连接，就可以讲话了。等交流结束，挂断电话结束此次交谈。 生活中的场景就解释了这工作原理。
'''
## 先从服务器端说起。服务器端先初始化Socket，然后与端口绑定(bind)，对端口进行监听(listen)，
调用accept阻塞，等待客户端连接。在这时如果有个客户端初始化一个Socket，然后连接服务器
(connect)，如果连接成功，这时客户端与服务器端的连接就建立了。客户端发送数据请求，服务器端接收请
求并处理请求，然后把回应数据发送给客户端，客户端读取数据，最后关闭连接，一次交互结束

---

<!-- p.196 -->

3-1 基础用法
### 服务端.py
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，绑定手机卡
phone.bind(('127.0.0.1',8080))
## 3，开机
phone.listen(5) ## 5 值得是半连接池的大小
print(f'服务端启动，服务运行在127.0.0.1:8080')
## 4，等待电话连接请求，拿到电话连接conn
conn,alient_addr = phone.accept() ## 是个元祖
print(conn) ## 套接字对象
print('客户端的IP和端口',alient_addr) ## 客户端的IP和端口 ('127.0.0.1', 57424)
## 5，通信：收消息/发消息
data = conn.recv(1024) ## 1024 指最大接受的数据量为1024Bytes,收到的是Bytes类型
print('客户端发来的消息：',data.decode('utf-8'))
conn.send(data.upper())
## 6，关闭电话连接(一个电话连接结束了就应该断掉)
conn.close() ## 挂断电话
## 7，可选：关机手机
phone.close()
### 客户端.py
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，拨通服务端电话
## 服务端的IP和端口
phone.connect(('127.0.0.1',8080)) ##
## 3.通信
phone.send('hello aini 哈哈哈哈'.encode('utf-8')) ## 发送的是bytes类型的
data = phone.recv(1024)
print(data.decode('utf-8'))
## 4,关闭连接（必选)
phone.close()

---

<!-- p.197 -->

3-2 通信循环
## 服务端.py
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，绑定手机卡
phone.bind(('127.0.0.1',8080))
## 3，开机
phone.listen(5) ## 5 值得是半连接池的大小
print(f'服务端启动，服务运行在127.0.0.1:8080')
## 4，等待电话连接请求，拿到电话连接conn
conn,alient_addr = phone.accept() ## 是个元祖
print(conn) ## 套接字对象
print('客户端的IP和端口',alient_addr) ## 客户端的IP和端口 ('127.0.0.1', 57424)
## 5，通信：收消息/发消息
while True:
data = conn.recv(1024) ## 1024 指最大接受的数据量为1024Bytes,收到的是Bytes类
型
print('客户端发来的消息：',data.decode('utf-8'))
conn.send(data.upper())
## 6，关闭电话连接(一个电话连接结束了就应该断掉)
conn.close() ## 挂断电话
## 7，可选：关机手机
phone.close()
## 客户端.py
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，拨通服务端电话
## 服务端的IP和端口
phone.connect(('127.0.0.1',8080)) ##
## 3.通信
while True:
user_input = input(">>>>>:").strip()
if user_input == 'quit': break
phone.send(user_input.encode('utf-8')) ## 发送的是bytes类型的
data = phone.recv(1024)

---

<!-- p.198 -->

3-3 socket收发消息的原理
3-4 修复bug1 (空格-阻塞)
print(data.decode('utf-8'))
## 4,关闭连接（必选)
phone.close()
## 客户端收发 和 服务端收发是独立的，并不是一次发对应一次收
## 客户端sned都是数据交给缓存，让操作系统调度网卡发，服务端发数据也是，而不是客户端和服务端直接
一对一的传输
## bug 原因：输入空格以后，input时被去掉空格了，等于user_input = ''
## 客户端可以send的空容缓存，再由网卡发送，由于空数据，等于没数据，所以不会发空数据的
## 修正： 判断user_input 的长度
## 客户端.py
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，拨通服务端电话
## 服务端的IP和端口
phone.connect(('127.0.0.1',8080)) ##
## 3.通信
while True:
user_input = input(">>>>>:").strip()
if user_input == 'quit': break
if len(user_input) == 0: continue
phone.send(user_input.encode('utf-8')) ## 发送的是bytes类型的
data = phone.recv(1024)

---

<!-- p.199 -->

3-5 bug2(客户端非正常死亡------导致服务端也异常)
3-6 链接循环（让服务端一直提供服务）
print(data.decode('utf-8'))
## 4,关闭连接（必选)
phone.close()
### 客户端直接关机，非正常停止脚本
# window 服务端异常：ConnectionReseatError
# Linux ： 通讯死循环（不断收空内容)
## 在unix系统中，一旦data收到的是空
## 意味着是以后昂异常行为：客户端非法断开了链接
## 解决服务端bug
# linix: 服务端添加判断内容，对客户端传过来的数据进行判断，如果为空，直接break,
## 针对linix 系统修复bug
## 5，通信：收消息/发消息
while True:
data = conn.recv(1024) ## 1024 指最大接受的数据量为1024Bytes,收到的是Bytes类
型
if len(data) == 0: break ## 空内容意味着异常，直接break
print('客户端发来的消息：',data.decode('utf-8'))
conn.send(data.upper())
## 针对Windows系统修复bug(添加异常处理)
while True:
try:
data = conn.recv(1024) ## 1024 指最大接受的数据量为1024Bytes,收到的是
Bytes类型
print('客户端发来的消息：',data.decode('utf-8'))
conn.send(data.upper())
except Exception:
## 6，关闭电话连接(一个电话连接结束了就应该断掉)
conn.close() ## 挂断电话
break
## 服务端满足的条件，应该一直提供服务--------------添加链接循环
## 服务端代码
import socket
## 以打电话为例
# 1，买手机
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
phone = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
## 2，绑定手机卡
phone.bind(('127.0.0.1',8080))
## 3，开机

---

<!-- p.200 -->

3-7半链接池
10.8 基于UDP写一个套接字通信
phone.listen(5) ## 5 值得是半连接池的大小
print(f'服务端启动，服务运行在127.0.0.1:8080')
## 链接循环
while True:
## 4，等待电话连接请求，拿到电话连接conn
conn,alient_addr = phone.accept() ## 是个元祖
print(conn) ## 套接字对象
print('客户端的IP和端口',alient_addr) ## 客户端的IP和端口 ('127.0.0.1',
57424)
## 5，通信：收消息/发消息
while True:
try:
data = conn.recv(1024) ## 1024 指最大接受的数据量为1024Bytes,收到的
是Bytes类型
print('客户端发来的消息：',data.decode('utf-8'))
conn.send(data.upper())
except Exception:
## 6，关闭电话连接(一个电话连接结束了就应该断掉)
conn.close() ## 挂断电话
break
phone.close()
phone.listen(5) ## 5 值得是半连接池的大小
## 如果不是并发编程，服务端只能与一个链接进行会话，其他客户端的链接进入半连接池，等待链接，如果
超过了半连接池的大小，则客户端无法跟服务端进行连接
## 服务端
import socket
## socket.SOCK_STREAM(流式协议) === TCP协议 sock.SOCK_DGRAM ===== UDP协议
server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
server.bind(('127.0.0.1',8080))
print(f'服务端启动，服务运行在127.0.0.1:8080')
while True:
data,client_adddr = server.recvfrom(1024)
print(data)
print(client_adddr)
server.sendto(data.decode('utf-8').upper().encode('utf-8'),
client_adddr)
server.close()
## 服务端可以发送空数据
## 客户端断了，服务端不会有影响

---

<!-- p.201 -->

10.9 粘包
10.9.1 粘包出现的原因及解决方案
## 客户端
import socket
## socket.SOCK_STREAM(流式协议) === TCP协议 socket.SOCK_DGRAM ===== UDP协议
client = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
while True:
user_input = input(">>>>>:").strip()
client.sendto(user_input.encode('utf-8'),('127.0.0.1',8080))
data,server_addr = client.recvfrom(1024)
print(data.decode('utf-8'),server_addr)
client.close()
## 须知：只有TCP有粘包现象，UDP永远不会粘包，为何，且听我娓娓道来
## 首先需要掌握一个socket收发消息的原理
## 所谓粘包问题主要还是因为接收方不知道消息之间的界限，不知道一次性提取多少字节的数据所造成的。
## tcp是流式协议。数据像水流一样粘在一起，没有任何边界区分
# 两种情况下会发生粘包。
##发送端需要等缓冲区满才发送出去，造成粘包（发送数据时间间隔很短，数据了很小，会合到一起，产
生粘包）
## 服务端
#_*_coding:utf-8_*_
__author__ = 'Linhaifeng'
from socket import *
ip_port=('127.0.0.1',8080)
tcp_socket_server=socket(AF_INET,SOCK_STREAM)
tcp_socket_server.bind(ip_port)
tcp_socket_server.listen(5)
conn,addr=tcp_socket_server.accept()
data1=conn.recv(10)
data2=conn.recv(10)
print('----->',data1.decode('utf-8'))
print('----->',data2.decode('utf-8'))
conn.close()
## 客户端
#_*_coding:utf-8_*_
__author__ = 'Linhaifeng'
import socket
BUFSIZE=1024

---

<!-- p.202 -->

ip_port=('127.0.0.1',8080)
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
res=s.connect_ex(ip_port)
s.send('hello'.encode('utf-8'))
s.send('feng'.encode('utf-8'))
## 接收方不及时接收缓冲区的包，造成多个包接收（客户端发送了一段数据，服务端只收了一小部分，
服务端下次再收的时候还是从缓冲区拿上次遗留的数据，产生粘包）
## 服务端
#_*_coding:utf-8_*_
__author__ = 'Linhaifeng'
from socket import *
ip_port=('127.0.0.1',8080)
tcp_socket_server=socket(AF_INET,SOCK_STREAM)
tcp_socket_server.bind(ip_port)
tcp_socket_server.listen(5)
conn,addr=tcp_socket_server.accept()
data1=conn.recv(2) #一次没有收完整
data2=conn.recv(10)#下次收的时候,会先取旧的数据,然后取新的
print('----->',data1.decode('utf-8'))
print('----->',data2.decode('utf-8'))
conn.close()
## 客户端
#_*_coding:utf-8_*_
__author__ = 'Linhaifeng'
import socket
BUFSIZE=1024
ip_port=('127.0.0.1',8080)
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
res=s.connect_ex(ip_port)
s.send('hello feng'.encode('utf-8'))
## 收数据没收干净，有残留，就跟下一次结果混在一起
## 解决的核心法门就是：每次都收干净，不要有残留
'''
此外，发送方引起的粘包是由TCP协议本身造成的，TCP为提高传输效率，发送方往往要收集到足够多的数据后
才发送一个TCP段。若连续几次需要send的数据都很少，通常TCP会根据优化算法把这些数据合成一个TCP段
后一次发送出去，这样接收方就收到了粘包数据。

---

<!-- p.203 -->

####
10.9.2 粘包问题普通解决（不是很好的解决方法）
10.9.3 自定义协议解决粘包问题
TCP（transport control protocol，传输控制协议）是面向连接的，面向流的，提供高可靠性服务。收
发两端（客户端和服务器端）都要有一一成对的socket，因此，发送端为了将多个发往接收端的包，更有效的
发到对方，使用了优化方法（Nagle算法），将多次间隔较小且数据量小的数据，合并成一个大的数据块，然
后进行封包。这样，接收端，就难于分辨出来了，必须提供科学的拆包机制。 即面向流的通信是无消息保护边
界的。
UDP（user datagram protocol，用户数据报协议）是无连接的，面向消息的，提供高效率服务。不会使
用块的合并优化算法，, 由于UDP支持的是一对多的模式，所以接收端的skbuff(套接字缓冲区）采用了链式
结构来记录每一个到达的UDP包，在每个UDP包中就有了消息头（消息来源地址，端口等信息），这样，对于接
收端来说，就容易进行区分处理了。 即面向消息的通信是有消息保护边界的。
tcp是基于数据流的，于是收发的消息不能为空，这就需要在客户端和服务端都添加空消息的处理机制，防止
程序卡住，而udp是基于数据报的，即便是你输入的是空内容（直接回车），那也不是空消息，udp协议会帮你
封装上消息头，实验略
'''
## 第一种解决方法：-----------该接受的最大字节数（但不是很好的办法，也不能无限放大）
while True:
msg = input(">>>：").strip()
if len(msg) == 0: continue
client.send(msg.encode('utf-8'))
res = client.recv(70000) ## 本次接受最大接受1024个字节
print(res.decode('gbk'),end=' ')
## 解决方法二
while True:
msg = input(">>>：").strip()
if len(msg) == 0: continue
client.send(msg.encode('utf-8'))
lang = 1024
while lang> 1023:
res = client.recv(1024) ## 本次接受最大接受1024个字节
lang = len(res)
print(res.decode('gbk'),end=' ')
## 先收固定长度的头：解析出数据的描述信息，包括数据的总大小total_size
## 根据解析出的描述信息，total_size
## 服务端
from socket import *
import subprocess
import struct
## 服务端应该满足两个条件
## 第一件事：一直对外提供服务
## 第二件事：能够并发的给多个服务端提供服务

---

<!-- p.204 -->

server = socket(AF_INET,SOCK_STREAM)
server.bind(('127.0.0.1',8080))
server.listen(5)
## 第一件事：循环的从半连接池中取出链接请求，与其建立双向链接，拿到链接对象
while True:
con,client_addr = server.accept()
## 第二件事：拿到链接对象，与其进行通信循环
while True:
try:
res = con.recv(1024) ## 最大8096 就可以
if len(res) == 0: break
obj = subprocess.Popen(
res.decode('utf-8'),
shell = True,
stdout = subprocess.PIPE,
stderr = subprocess.PIPE
)
std_succ = obj.stdout.read() ## 拿到的结果都是是字节类型，但是window
编码用的是gbk
std_err = obj.stderr.read()
total_size = len(std_succ) + len(std_err)
## 先发头信息（固定长度的bytes)：对数据的描述信息
header = struct.pack('i',total_size) ## 把数字处理成长度固定的四个字
节
con.send(header)
## 发送正确内容
con.send(std_succ)
## 发送错误内容
con.send(std_err)
except Exception:
break
## 客户端
from socket import *
import struct
client = socket(AF_INET,SOCK_STREAM)
client.connect(('127.0.0.1',8080))
while True:
msg = input(">>>：").strip()
if len(msg) == 0: continue
client.send(msg.encode('utf-8'))
header = client.recv(4) ## 拿到数据总长度
total_size = struct.unpack('i',header)[0] ## 解析数据总长度
rec_size = 0
while rec_size < total_size:
res = client.recv(1024) ## 本次接受最大接受1024个字节
rec_size += len(res)
print(res.decode('gbk'),end=' ')
else:
print()

---

<!-- p.205 -->

10.9.4 解决粘包终极大招
## 服务端
from socket import *
import subprocess
import struct
from hashlib import md5
import json
server = socket(AF_INET,SOCK_STREAM)
server.bind(('127.0.0.1',8080))
server.listen(5)
rn bs
## 第一件事：循环的从半连接池中取出链接请求，与其建立双向链接，拿到链接对象
while True:
con,client_addr = server.accept()
## 第二件事：拿到链接对象，与其进行通信循环
while True:
try:
res = con.recv(1024) ## 最大8096就可以
if len(res) == 0: break
obj = subprocess.Popen(
res.decode('utf-8'),
shell = True,
stdout = subprocess.PIPE,
stderr = subprocess.PIPE
)
std_succ = obj.stdout.read() ## 拿到的结果都是是字节类型，但是window
编码用的是gbk
std_err = obj.stderr.read()
total_size = len(std_succ) + len(std_err)
## 制作头
header = {
'filename':'a.txt',
'total_size':total_size,
'md5':'ainiainiainiaini'
}
str_json = json.dumps(header)
json_str_bytes = str_json.encode('utf-8')
## 先发头布长度信息
header_size = struct.pack('i',len(json_str_bytes))
con.send(header_size)
## 发送头部
con.send(json_str_bytes)
## 发送正确内容
con.send(std_succ)
## 发送错误内容
con.send(std_err)
except Exception:

---

<!-- p.206 -->

10.10 socketserver模块实现并发
10.10.1 基于TCP协议并发
break
# 客户端
from socket import *
import struct
import json
client = socket(AF_INET,SOCK_STREAM)
client.connect(('127.0.0.1',8080))
while True:
msg = input(">>>：").strip()
if len(msg) == 0: continue
client.send(msg.encode('utf-8'))
## 收四个字节的头部长度
header_size_bytes = client.recv(4) ## 拿到数据总长度
header_size = struct.unpack('i',header_size_bytes)[0] ## 解析头部总长度
## 根据头部长度，读取头部信息
header = client.recv(header_size).decode('utf-8')
header_dic = json.loads(header)
print(header_dic)
## 拿到数据大小
total_size = header_dic.get('total_size')
rec_size = 0
while rec_size < total_size:
res = client.recv(1024) ## 本次接受最大接受1024个字节
rec_size += len(res)
print(res.decode('gbk'),end=' ')
else:
print()
## 服务端
import socketserver
class MyRequestHandele(socketserver.BaseRequestHandler):
def handle(self):
while True:
try:
res = self.request.recv(1024) ## 最大8096 就可以
if len(res) == 0: break
self.request.send(res.upper())
except Exception:
break
self.request.close()
s = socketserver.ThreadingTCPServer(('127.0.0.1',8888),MyRequestHandele)
s.serve_forever()

---

<!-- p.207 -->

10.10.2 基于UDP协议并发
七，并发编程
11.1 操作系统发展史
参考博客即可:https://www.cnblogs.com/Dominic-Ji/articles/10929381.html
## 客户端
from socket import *
client = socket(AF_INET, SOCK_STREAM)
client.connect(('127.0.0.1', 8888))
while True:
msg = input(">>>：").strip()
if len(msg) == 0: continue
client.send(msg.encode('utf-8'))
res = client.recv(1024) ## 本次接受最大接受1024个字节
print(res.decode('utf-8'))
## 服务端
import socketserver
class MyRequestHandle(socketserver.BaseRequestHandler):
def handle(self):
client_data = self.request[0]
server = self.request[1] # 套接字对象
client_addr = self.client_address
print(client_data)
server.sendto(client_data.upper(),client_addr)
s = socketserver.ThreadingUDPServer(('127.0.0.1',8080),MyRequestHandle)
s.serve_forever()
## 客户端
import socket
## socket.SOCK_STREAM(流式协议) === TCP协议 socket.SOCK_DGRAM ===== UDP协议
client = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
while True:
user_input = input(">>>>>:").strip()
client.sendto(user_input.encode('utf-8'),('127.0.0.1',8080))
data,server_addr = client.recvfrom(1024)
print(data.decode('utf-8'),server_addr)
client.close()

---

<!-- p.208 -->

11.1.1 多道技术
单核实现并发的效果
11.1.2 必备知识点
并发
看起来像同时运行的就可以称之为并发
并行
真正意义上的同时执行
ps:
并行肯定算并发
单核的计算机肯定不能实现并行，但是可以实现并发！！！
补充：我们直接假设单核就是一个核，干活的就一个人，不要考虑cpu里面的内核数
11.1.3 多道技术重点知识
空间上的服用与时间上的服用
空间上的复用
多个程序公用一套计算机硬件
时间上的复用
例子:洗衣服30s，做饭50s，烧水30s
单道需要110s，多道只需要任务做长的那一个 切换节省时间
例子:边吃饭边玩游戏 保存状态
切换+保存状态
11.2 进程理论
11.2.1 必备知识点
程序与进程的区别
"""
切换(CPU)分为两种情况
1.当一个程序遇到IO操作的时候，操作系统会剥夺该程序的CPU执行权限
作用:提高了CPU的利用率 并且也不影响程序的执行效率
2.当一个程序长时间占用CPU的时候，操作吸引也会剥夺该程序的CPU执行权限
弊端:降低了程序的执行效率(原本时间+切换时间)
"""
"""
程序就是一堆躺在硬盘上的代码，是“死”的
进程则表示程序正在执行的过程，是“活”的
"""

---

<!-- p.209 -->

11.2.2 进程调度
先来先服务调度算法
短作业优先调度算法
时间片轮转法+多级反馈队列
参考图解
11.2.3 进程运行的三状态图
参考图解了解即可
11.2.4 两对重要概念
同步和异步
阻塞非阻塞
上述概念的组合:最高效的一种组合就是异步非阻塞
11.3 开启进程的两种方式
定心丸:代码开启进程和线程的方式，代码书写基本是一样的，你学会了如何开启进程就学会了如何开启
线程
"""对长作业有利，对短作业无益"""
"""对短作业有利，多长作业无益"""
"""描述的是任务的提交方式"""
同步:任务提交之后，原地等待任务的返回结果，等待的过程中不做任何事(干等)
程序层面上表现出来的感觉就是卡住了
异步:任务提交之后，不原地等待任务的返回结果，直接去做其他事情
我提交的任务结果如何获取？
任务的返回结果会有一个异步回调机制自动处理
"""描述的程序的运行状态"""
阻塞:阻塞态
非阻塞:就绪态、运行态
理想状态:我们应该让我们的写的代码永远处于就绪态和运行态之间切换
from multiprocessing import Process
import time
def task(name):
print('%s is running'%name)
time.sleep(3)
print('%s is over'%name)

---

<!-- p.210 -->

总结
11.4 join方法
join是让主进程等待子进程代码运行结束之后，再继续运行。不影响其他子进程的执行
## 在window系统中，创建进程一定在main下面下
## 因为window下创建进程类似于模块带入方式
if __name__ == '__main__':
# 1 创建一个对象
p = Process(target=task, args=('jason',))
# 容器类型哪怕里面只有1个元素 建议要用逗号隔开
# 2 开启进程
p.start() # 告诉操作系统帮你创建一个进程 异步
print('主')
# 第二种方式 类的继承
from multiprocessing import Process
import time
class MyProcess(Process):
def run(self):
print('hello bf girl')
time.sleep(1)
print('get out!')
if __name__ == '__main__':
p = MyProcess()
p.start()
print('主')
"""
创建进程就是在内存中申请一块内存空间将需要运行的代码丢进去
一个进程对应在内存中就是一块独立的内存空间
多个进程对应在内存中就是多块独立的内存空间
进程与进程之间数据默认情况下是无法直接交互,如果想交互可以借助于第三方工具、模块
"""
from multiprocessing import Process
import time
def task(name, n):
print('%s is running'%name)
time.sleep(n)
print('%s is over'%name)
if __name__ == '__main__':
# p1 = Process(target=task, args=('jason', 1))
# p2 = Process(target=task, args=('egon', 2))
# p3 = Process(target=task, args=('tank', 3))

---

<!-- p.211 -->

11.5 进程之间数据相互隔离
11.6 人工智能相关网站
http://www.turingapi.com/
https://www.xfyun.cn/?ch=bd05&b_scene_zt=1
http://ai.baidu.com/creation/main/demo
作为一名python程序员当你遇到一个功能的时候，第一时间你可以考虑是否有对应的模块已经帮你实现
了该功能
11.7 进程对象及其他方法
# start_time = time.time()
# p1.start()
# p2.start()
# p3.start() # 仅仅是告诉操作系统要创建进程
# # time.sleep(50000000000000000000)
# # p.join() # 主进程等待子进程p运行结束之后再继续往后执行
# p1.join()
# p2.join()
# p3.join()
start_time = time.time()
p_list = []
for i in range(1, 4):
p = Process(target=task, args=('子进程%s'%i, i))
p.start()
p_list.append(p)
for p in p_list:
p.join()
print('主', time.time() - start_time)
from multiprocessing import Process
money = 100
def task():
global money # 局部修改全局
money = 666 ## 其实也修改了money的值，但是改的只是自己进程里的，外面的没改
print('子',money) ## 666
if __name__ == '__main__':
p = Process(target=task)
p.start()
p.join()
print(money) ## 100
"""
一台计算机上面运行着很多进程，那么计算机是如何区分并管理这些进程服务端的呢？
计算机会给每一个运行的进程分配一个PID号
如何查看
windows电脑

---

<!-- p.212 -->

11.8 僵尸进程与孤儿进程(了解)
11. 9 守护进程
进入cmd输入tasklist即可查看
tasklist |findstr PID查看具体的进程
mac电脑
进入终端之后输入ps aux
ps aux|grep PID查看具体的进程
"""
from multiprocessing import Process, current_process
current_process().pid # 查看当前进程的进程号
import os
os.getpid() # 查看当前进程进程号
os.getppid() # 查看当前进程的父进程进程号
p.terminate() # 杀死当前进程
# 是告诉操作系统帮你去杀死当前进程 但是需要一定的时间 而代码的运行速度极快
time.sleep(0.1)
print(p.is_alive()) # 判断当前进程是否存活
# 僵尸进程
"""
死了但是没有死透
当你开设了子进程之后 该进程死后不会立刻释放占用的进程号
因为我要让父进程能够查看到它开设的子进程的一些基本信息 占用的pid号 运行时间。。。
所有的进程都会步入僵尸进程
父进程不死并且在无限制的创建子进程并且子进程也不结束
回收子进程占用的pid号
父进程等待子进程运行结束
父进程调用join方法
"""
# 孤儿进程
"""
子进程存活，父进程意外死亡
操作系统会开设一个“儿童福利院”专门管理孤儿进程回收相关资源
"""
from multiprocessing import Process
import time
def task(name):
print('%s总管正在活着'% name)
time.sleep(3)
print('%s总管正在死亡' % name)
if __name__ == '__main__':
p = Process(target=task,args=('egon',))
# p = Process(target=task,kwargs={'name':'egon'})

---

<!-- p.213 -->

11.10 互斥锁
多个进程操作同一份数据的时候，会出现数据错乱的问题
针对上述问题，解决方式就是加锁处理:将并发变成串行，牺牲效率但是保证了数据的安全
p.daemon = True # 将进程p设置成守护进程 这一句一定要放在start方法上面才有效否则会直接
报错
p.start()
print('皇帝jason寿终正寝')
from multiprocessing import Process, Lock
import json
import time
import random
# 查票
def search(i):
# 文件操作读取票数
with open('data','r',encoding='utf8') as f:
dic = json.load(f)
print('用户%s查询余票：%s'%(i, dic.get('ticket_num')))
# 字典取值不要用[]的形式 推荐使用get 你写的代码打死都不能报错！！！
# 买票 1.先查 2.再买
def buy(i):
# 先查票
with open('data','r',encoding='utf8') as f:
dic = json.load(f)
# 模拟网络延迟
time.sleep(random.randint(1,3))
# 判断当前是否有票
if dic.get('ticket_num') > 0:
# 修改数据库 买票
dic['ticket_num'] -= 1
# 写入数据库
with open('data','w',encoding='utf8') as f:
json.dump(dic,f)
print('用户%s买票成功'%i)
else:
print('用户%s买票失败'%i)
# 整合上面两个函数
def run(i, mutex):
search(i)
# 给买票环节加锁处理
# 抢锁
mutex.acquire()
buy(i)
# 释放锁
mutex.release()

---

<!-- p.214 -->

11.11进程间通信
11.11.1队列Queue模块
if __name__ == '__main__':
# 在主进程中生成一把锁 让所有的子进程抢 谁先抢到谁先买票
mutex = Lock()
for i in range(1,11):
p = Process(target=run, args=(i, mutex))
p.start()
"""
扩展 行锁 表锁
注意：
1.锁不要轻易的使用，容易造成死锁现象(我们写代码一般不会用到，都是内部封装好的)
2.锁只在处理数据的部分加来保证数据安全(只在争抢数据的环节加锁处理即可)
"""
"""
管道:subprocess
stdin stdout stderr
队列:管道+锁
队列:先进先出
堆栈:先进后出
"""
from multiprocessing import Queue
# 创建一个队列
q = Queue(5) # 括号内可以传数字 标示生成的队列最大可以同时存放的数据量
# 往队列中存数据
q.put(111)
q.put(222)
q.put(333)
# print(q.full()) # 判断当前队列是否满了
# print(q.empty()) # 判断当前队列是否空了
q.put(444)
q.put(555)
# print(q.full()) # 判断当前队列是否满了
# q.put(666) # 当队列数据放满了之后 如果还有数据要放程序会阻塞 直到有位置让出来 不会报错
"""
存取数据 存是为了更好的取
千方百计的存、简单快捷的取
同在一个屋檐下
差距为何那么大
"""
# 去队列中取数据
v1 = q.get()
v2 = q.get()
v3 = q.get()
v4 = q.get()

---

<!-- p.215 -->

11.11.2 IPC机制
11.11.3 生产者消费者模型
v5 = q.get()
# print(q.empty())
# V6 = q.get_nowait() # 没有数据直接报错queue.Empty
# v6 = q.get(timeout=3) # 没有数据之后原地等待三秒之后再报错 queue.Empty
try:
v6 = q.get(timeout=3)
print(v6)
except Exception as e:
print('一滴都没有了!')
# # v6 = q.get() # 队列中如果已经没有数据的话 get方法会原地阻塞
# print(v1, v2, v3, v4, v5, v6)
"""
q.full()
q.empty()
q.get_nowait()
在多进程的情况下是不精确
"""
from multiprocessing import Queue, Process
"""
研究思路
1.主进程跟子进程借助于队列通信
2.子进程跟子进程借助于队列通信
"""
def producer(q):
q.put('我是23号技师 很高兴为您服务')
def consumer(q):
print(q.get()) ## '我是23号技师 很高兴为您服务'
if __name__ == '__main__':
q = Queue()
p = Process(target=producer,args=(q,))
p1 = Process(target=consumer,args=(q,))
p.start()
p1.start()
"""
生产者:生产/制造东西的
消费者:消费/处理东西的
该模型除了上述两个之外还需要一个媒介
生活中的例子做包子的将包子做好后放在蒸笼(媒介)里面，买包子的取蒸笼里面拿
厨师做菜做完之后用盘子装着给你消费者端过去
生产者和消费者之间不是直接做交互的，而是借助于媒介做交互
生产者(做包子的) + 消息队列(蒸笼) + 消费者(吃包子的)
"""

---

<!-- p.216 -->

11.12 线程
from multiprocessing import Process, Queue, JoinableQueue
import time
import random
def producer(name,food,q):
for i in range(5):
data = '%s生产了%s%s'%(name,food,i)
# 模拟延迟
time.sleep(random.randint(1,3))
print(data)
# 将数据放入 队列中
q.put(data)
def consumer(name,q):
# 消费者胃口很大 光盘行动
while True:
food = q.get() # 没有数据就会卡住
# 判断当前是否有结束的标识
# if food is None:break
time.sleep(random.randint(1,3))
print('%s吃了%s'%(name,food))
q.task_done() # 告诉队列你已经从里面取出了一个数据并且处理完毕了
if __name__ == '__main__':
# q = Queue()
q = JoinableQueue()
p1 = Process(target=producer,args=('大厨egon','包子',q))
p2 = Process(target=producer,args=('马叉虫tank','泔水',q))
c1 = Process(target=consumer,args=('春哥',q))
c2 = Process(target=consumer,args=('新哥',q))
p1.start()
p2.start()
# 将消费者设置成守护进程
c1.daemon = True
c2.daemon = True
c1.start()
c2.start()
p1.join()
p2.join()
# 等待生产者生产完毕之后 往队列中添加特定的结束符号
# q.put(None) # 肯定在所有生产者生产的数据的末尾
# q.put(None) # 肯定在所有生产者生产的数据的末尾
q.join() # 等待队列中所有的数据被取完再执行往下执行代码
"""
JoinableQueue 每当你往该队列中存入数据的时候 内部会有一个计数器+1
没当你调用task_done的时候 计数器-1
q.join() 当计数器为0的时候 才往后运行
"""
# 只要q.join执行完毕 说明消费者已经处理完数据了 消费者就没有存在的必要了

---

<!-- p.217 -->

11.12.1 什么是线程
11.12.2 为何要有线程
11.12.3 开启线程的两种方式
"""
进程:资源单位
线程:执行单位
将操作系统比喻成一个大的工厂
那么进程就相当于工厂里面的车间
而线程就是车间里面的流水线
每一个进程肯定自带一个线程
再次总结:
进程:资源单位(起一个进程仅仅只是在内存空间中开辟一块独立的空间)
线程:执行单位(真正被cpu执行的其实是进程里面的线程，线程指的就是代码的执行过程，执行代码中所
需要使用到的资源都找所在的进程索要)
进程和线程都是虚拟单位，只是为了我们更加方便的描述问题
"""
"""
开设进程
1.申请内存空间 耗资源
2.“拷贝代码” 耗资源
开线程
一个进程内可以开设多个线程，在用一个进程内开设多个线程无需再次申请内存空间操作
总结:
开设线程的开销要远远的小于进程的开销
同一个进程下的多个线程数据是共享的!!!
"""
我们要开发一款文本编辑器
获取用户输入的功能
实时展示到屏幕的功能
自动保存到硬盘的功能
针对上面这三个功能，开设进程还是线程合适？？？
开三个线程处理上面的三个功能更加的合理
## 第一种方法
from multiprocessing import Process
from threading import Thread
import time
def task(name):
print('%s is running'%name)
time.sleep(1)
print('%s is over'%name)
# # 开启线程不需要在main下面执行代码 直接书写就可以
# # 但是我们还是习惯性的将启动命令写在main下面

---

<!-- p.218 -->

11.12.4 TCP协议实现并发
t = Thread(target=task,args=('egon',))
p = Process(target=task,args=('jason',))
p.start()
t.start() # 创建线程的开销非常小 几乎是代码一执行线程就已经创建了
print('主')
## 第二种方法
from threading import Thread
import time
class MyThead(Thread):
def __init__(self, name):
"""针对刷个下划线开头双下滑线结尾(__init__)的方法 统一读成 双下init"""
# 重写了别人的方法 又不知道别人的方法里有啥 你就调用父类的方法
super().__init__()
self.name = name
def run(self):
print('%s is running'%self.name)
time.sleep(1)
print('egon DSB')
if __name__ == '__main__':
t = MyThead('egon')
t.start()
print('主')
import socket
from threading import Thread
from multiprocessing import Process
"""
服务端
1.要有固定的IP和PORT
2.24小时不间断提供服务
3.能够支持并发
从现在开始要养成一个看源码的习惯
我们前期要立志称为拷贝忍者 卡卡西 不需要有任何的创新
等你拷贝到一定程度了 就可以开发自己的思想了
"""
server =socket.socket() # 括号内不加参数默认就是TCP协议
server.bind(('127.0.0.1',8080))
server.listen(5)
# 将服务的代码单独封装成一个函数
def talk(conn):
# 通信循环
while True:
try:
data = conn.recv(1024)
# 针对mac linux 客户端断开链接后

---

<!-- p.219 -->

11.12.5 线程对象的join方法
11.12.6，同一个进程下的多个线程数据是共享的
if len(data) == 0: break
print(data.decode('utf-8'))
conn.send(data.upper())
except ConnectionResetError as e:
print(e)
break
conn.close()
# 链接循环
while True:
conn, addr = server.accept() # 接客
# 叫其他人来服务客户
# t = Thread(target=talk,args=(conn,))
t = Process(target=talk,args=(conn,))
t.start()
"""客户端"""
import socket
client = socket.socket()
client.connect(('127.0.0.1',8080))
while True:
client.send(b'hello world')
data = client.recv(1024)
print(data.decode('utf-8'))
from threading import Thread
import time
def task(name):
print('%s is running'%name)
time.sleep(3)
print('%s is over'%name)
if __name__ == '__main__':
t = Thread(target=task,args=('egon',))
t.start()
t.join() # 主线程等待子线程运行结束再执行
print('主')
from threading import Thread
import time
money = 100
def task():
global money

---

<!-- p.220 -->

11.12.7 线程对象属性及其他方法
11.12.8 守护线程
money = 666
print(money) ### 666
if __name__ == '__main__':
t = Thread(target=task)
t.start()
t.join()
print(money) ## 666
from threading import Thread, active_count, current_thread
import os,time
def task(n):
# print('hello world',os.getpid())
print('hello world',current_thread().name)
time.sleep(n)
if __name__ == '__main__':
t = Thread(target=task,args=(1,))
t1 = Thread(target=task,args=(2,))
t.start()
t1.start()
t.join()
print('主',active_count()) # 统计当前正在活跃的线程数
# print('主',os.getpid())
# print('主',current_thread().name) # 获取线程名字
from threading import Thread
import time
def task(name):
print('%s is running'%name)
time.sleep(1)
print('%s is over'%name) ## 这句话不会执行，主线程结束了以后，子线程也就结束了
if __name__ == '__main__':
t = Thread(target=task,args=('egon',))
t.daemon = True
t.start()
print('主')
"""
主线程运行结束之后不会立刻结束 会等待所有其他非守护线程结束才会结束
因为主线程的结束意味着所在的进程的结束
"""
# 稍微有一点迷惑性的例子
from threading import Thread
import time

---

<!-- p.221 -->

11.12.9 线程互斥锁
def foo():
print(123)
time.sleep(1)
print('end123')
def func():
print(456)
time.sleep(3)
print('end456')
if __name__ == '__main__':
t1 = Thread(target=foo)
t2 = Thread(target=func)
t1.daemon = True ## ts设置成主线程死了以后立马死掉，但是由于主线程运行完了以后还要等待
t2,所以不会立马死掉
t1.start()
t2.start()
print('主.......')
'''
123
456
主 ## 还要等待t2运行完，才会死掉
end123
end456
'''
from threading import Thread,Lock
import time
money = 100
mutex = Lock()
def task():
global money
mutex.acquire()
tmp = money
time.sleep(0.1)
money = tmp - 1
mutex.release()
if __name__ == '__main__':
t_list = []
for i in range(100):
t = Thread(target=task)
t.start()
t_list.append(t)
for t in t_list:
t.join()
print(money)

---

<!-- p.222 -->

11.12.10 GIL全局解释器锁
11.12.11 GIL与普通互斥锁的区别
"""
In CPython, the global interpreter lock, or GIL, is a mutex that prevents
multiple
native threads from executing Python bytecodes at once. This lock is necessary
mainly
because CPython’s memory management is not thread-safe. (However, since the GIL
exists, other features have grown to depend on the guarantees that it enforces.)
"""
"""
python解释器其实有多个版本
Cpython
Jpython
Pypypython
但是普遍使用的都是CPython解释器
在CPython解释器中GIL是一把互斥锁，用来阻止同一个进程下的多个线程的同时执行
同一个进程下的多个线程无法利用多核优势！！！
疑问:python的多线程是不是一点用都没有？？？无法利用多核优势
因为cpython中的内存管理不是线程安全的
内存管理(垃圾回收机制)
1.应用计数
2.标记清楚
3.分代回收
"""
"""
重点:
1.GIL不是python的特点而是CPython解释器的特点
2.GIL是保证解释器级别的数据的安全
3.GIL会导致同一个进程下的多个线程的无法同时执行即无法利用多核优势(******)
4.针对不同的数据还是需要加不同的锁处理
5.解释型语言的通病:同一个进程下多个线程无法利用多核优势
"""
from threading import Thread,Lock
import time
mutex = Lock()
money = 100
def task():
global money
# with mutex:
# tmp = money
# time.sleep(0.1)
# money = tmp -1
mutex.acquire()
tmp = money
time.sleep(0.1) # 只要你进入IO了 GIL会自动释放
money = tmp - 1

---

<!-- p.223 -->

11.12.12 同一个进程下的多线程无法利用多核优势,是不是就没有用
了
12-1 代码验证
mutex.release()
if __name__ == '__main__':
t_list = []
for i in range(100):
t = Thread(target=task)
t.start()
t_list.append(t)
for t in t_list:
t.join()
print(money)
"""
100个线程起起来之后 要先去抢GIL
我进入io GIL自动释放 但是我手上还有一个自己的互斥锁
其他线程虽然抢到了GIL但是抢不到互斥锁
最终GIL还是回到你的手上 你去操作数据
"""
"""
多线程是否有用要看具体情况
单核:四个任务(IO密集型\计算密集型)
多核:四个任务(IO密集型\计算密集型)
"""
# 计算密集型 每个任务都需要10s
## 单核(不用考虑了)
## 多进程:额外的消耗资源
## 多线程:介绍开销
## 多核
## 多进程:总耗时 10+
## 多线程:总耗时 40+
# IO密集型
## 多核
## 多进程:相对浪费资源
## 多线程:更加节省资源
## 计算密集型
from multiprocessing import Process
from threading import Thread
import os,time
def work():
res = 0
for i in range(10000000):
res *= i
if __name__ == '__main__':
l = []

---

<!-- p.224 -->

11.12.13 总结
11.13 死锁与递归锁（了解）
11.13.1 死锁
print(os.cpu_count()) # 获取当前计算机CPU个数
start_time = time.time()
for i in range(12):
p = Process(target=work) # 1.4679949283599854
t = Thread(target=work) # 5.698534250259399
t.start()
# p.start()
# l.append(p)
l.append(t)
for p in l:
p.join()
print(time.time()-start_time)
# IO密集型
from multiprocessing import Process
from threading import Thread
import os,time
def work():
time.sleep(2)
if __name__ == '__main__':
l = []
print(os.cpu_count()) # 获取当前计算机CPU个数
start_time = time.time()
for i in range(4000):
# p = Process(target=work) # 21.149890184402466
t = Thread(target=work) # 3.007986068725586
t.start()
# p.start()
# l.append(p)
l.append(t)
for p in l:
p.join()
print(time.time()-start_time)
"""
多进程和多线程都有各自的优势
并且我们后面在写项目的时候通常可以
多进程下面再开设多线程
这样的话既可以利用多核也可以介绍资源消耗
"""
## 当你知道锁的使用抢锁必须要释放锁，其实你在操作锁的时候也极其容易产生死锁现象(整个程序卡死 阻
塞)
from threading import Thread, Lock

---

<!-- p.225 -->

11.13.2 递归锁
import time
mutexA = Lock() ## 类不一样。产生的是不同的对象
mutexB = Lock()
# 类只要加括号多次 产生的肯定是不同的对象
# 如果你想要实现多次加括号等到的是相同的对象 单例模式
## 类实例化多次得到的都是同一个对象 ------------------- 单例模式
class MyThead(Thread):
def run(self):
self.func1()
self.func2()
def func1(self):
mutexA.acquire()
print('%s 抢到A锁'% self.name) # 获取当前线程名
mutexB.acquire()
print('%s 抢到B锁'% self.name)
mutexB.release()
mutexA.release()
def func2(self):
mutexB.acquire()
print('%s 抢到B锁'% self.name)
time.sleep(2)
mutexA.acquire()
print('%s 抢到A锁'% self.name) # 获取当前线程名
mutexA.release()
mutexB.release()
if __name__ == '__main__':
for i in range(10):
t = MyThead()
t.start()
from threading import Thread, Lock,Rlock()
"""
递归锁的特点
可以被连续的acquire和release
但是只能被第一个抢到这把锁执行上述操作
它的内部有一个计数器 每acquire一次计数加一 每realse一次计数减一
只要计数不为0 那么其他人都无法抢到该锁
"""
# 将上述的
mutexA = Lock()
mutexB = Lock()
# 换成
mutexA = mutexB = RLock()
## 只要有人抢锁count加一，释放锁count减一，
## 如11.13.1 所示
def func1(self):

---

<!-- p.226 -->

11.14 信号量（了解）
信号量在不同的阶段可能对应不同的技术点
在并发编程中信号量指的是锁!!!
11.15 Event事件（了解）
一些进程/线程需要等待另外一些进程/线程运行完毕之后才能运行，类似于发射信号一样
mutexA.acquire() ## AA抢到了 A锁 count = 1
print('%s 抢到A锁'% self.name) # 获取当前线程名
mutexB.acquire() ## AA抢到了 B锁 count = 2
print('%s 抢到B锁'% self.name)
mutexB.release() ## AA释放了 B锁 count = 1
mutexA.release() ## AA释放了 A锁 count = 0 count = 0 时其他人才可以抢，
所以不会出现死锁
def func2(self):
mutexB.acquire()
print('%s 抢到B锁'% self.name)
time.sleep(2)
mutexA.acquire()
print('%s 抢到A锁'% self.name) # 获取当前线程名
mutexA.release()
mutexB.release()
"""
如果我们将互斥锁比喻成一个厕所的话
那么信号量就相当于多个厕所
"""
from threading import Thread, Semaphore
import time
import random
"""
利用random模块实现打印随机验证码(搜狗的一道笔试题)
"""
sm = Semaphore(5) # 括号内写数字 写几就表示开设几个坑位
def task(name):
sm.acquire()
print('%s 正在蹲坑'% name)
time.sleep(random.randint(1, 5))
sm.release()
if __name__ == '__main__':
for i in range(20):
t = Thread(target=task, args=('伞兵%s号'%i, ))
t.start()
from threading import Thread, Event
import time

---

<!-- p.227 -->

11.16 线程Q（了解）
event = Event() # 造了一个红绿灯
def light():
print('红灯亮着的')
time.sleep(3)
print('绿灯亮了')
# 告诉等待红灯的人可以走了
event.set()
def car(name):
print('%s 车正在灯红灯'%name)
event.wait() # 等待别人给你发信号
print('%s 车加油门飙车走了'%name)
if __name__ == '__main__':
t = Thread(target=light)
t.start()
for i in range(20):
t = Thread(target=car, args=('%s'%i, ))
t.start()
"""
同一个进程下多个线程数据是共享的
为什么先同一个进程下还会去使用队列呢
因为队列是
管道 + 锁
所以用队列还是为了保证数据的安全
"""
import queue
# 我们现在使用的队列都是只能在本地测试使用
# 1 队列q 先进先出
# q = queue.Queue(3)
# q.put(1)
# q.get()
# q.get_nowait()
# q.get(timeout=3)
# q.full()
# q.empty()
# 后进先出q
# q = queue.LifoQueue(3) # last in first out
# q.put(1)
# q.put(2)
# q.put(3)
# print(q.get()) # 3

---

<!-- p.228 -->

11.17 进程池和线程池（掌握）
先回顾之前TCP服务端实现并发的效果是怎么玩的
每来一个人就开设一个进程或者线程去处理
11.17.1 线程池--进程池的基本使用
# 优先级q 你可以给放入队列中的数据设置进出的优先级
q = queue.PriorityQueue(4)
q.put((10, '111'))
q.put((100, '222'))
q.put((0, '333'))
q.put((-5, '444'))
print(q.get()) # (-5, '444')
# put括号内放一个元祖 第一个放数字表示优先级
# 需要注意的是 数字越小优先级越高!!!
"""
无论是开设进程也好还是开设线程也好 是不是都需要消耗资源
只不过开设线程的消耗比开设进程的稍微小一点而已
我们是不可能做到无限制的开设进程和线程的 因为计算机硬件的资源更不上！！！
硬件的开发速度远远赶不上软件呐
我们的宗旨应该是在保证计算机硬件能够正常工作的情况下最大限度的利用它
"""
# 池的概念
"""
什么是池?
池是用来保证计算机硬件安全的情况下最大限度的利用计算机
它降低了程序的运行效率但是保证了计算机硬件的安全 从而让你写的程序能够正常运行
"""
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import time
import os
# pool = ThreadPoolExecutor(5) # 池子里面固定只有五个线程
# 括号内可以传数字 不传的话默认会开设当前计算机cpu个数五倍的线程
pool = ProcessPoolExecutor(5)
# 括号内可以传数字 不传的话默认会开设当前计算机cpu个数进程
"""
池子造出来之后 里面会固定存在五个线程
这个五个线程不会出现重复创建和销毁的过程
池子造出来之后 里面会固定的几个进程
这个几个进程不会出现重复创建和销毁的过程
池子的使用非常的简单
你只需要将需要做的任务往池子中提交即可 自动会有人来服务你
"""
def task(n):
print(n,os.getpid())

---

<!-- p.229 -->

11.18.2 总结
time.sleep(2)
return n**n
## 回调函数
def call_back(n):
print('call_back>>>:',n.result()) ## 这里可以拿到结果
"""
任务的提交方式
同步:提交任务之后原地等待任务的返回结果 期间不做任何事
异步:提交任务之后不等待任务的返回结果 执行继续往下执行
返回结果如何获取？？？
异步提交任务的返回结果 应该通过回调机制来获取
回调机制
就相当于给每个异步任务绑定了一个定时炸弹
一旦该任务有结果立刻触发爆炸
"""
## 第一种：变运行任务，变打印结果
if __name__ == '__main__':
# pool.submit(task, 1) # 朝池子中提交任务 异步提交
# print('主')
t_list = []
for i in range(20): # 朝池子中提交20个任务
# res = pool.submit(task, i) # <Future at 0x100f97b38 state=running>
res = pool.submit(task, i).add_done_callback(call_back)
print(res.result()) # result方法 同步提交
t_list.append(res)
for t in t_list:
print('>>>:',t.result()) # 肯定是有序的
"""
程序有并发变成了串行
任务的为什么打印的是None：因为函数没有指定返回值
res.result() 拿到的就是异步提交的任务的返回结果
"""
## 第二种： 等待线程池中或进程池中所有的任务执行完毕之后再继续往下执行
if __name__ == '__main__':
t_list = []
for i in range(20): # 朝池子中提交20个任务
# res = pool.submit(task, i) # <Future at 0x100f97b38 state=running>
res = pool.submit(task, i).add_done_callback(call_back)
# 等待线程池中所有的任务执行完毕之后再继续往下执行
pool.shutdown() # 关闭线程池 等待线程池中所有的任务运行完毕
for t in t_list:
print('>>>:',t.result()) # 肯定是有序的
## 结果就是先运行完所有的任务，然后一起打印结果
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
pool = ProcessPoolExecutor(5)
pool.submit(task, i).add_done_callback(call_back)

---

<!-- p.230 -->

11.18 协程
11.18.1 验证切换是否就一定提升效率
"""
进程:资源单位
线程:执行单位
协程:这个概念完全是程序员自己意淫出来的 根本不存在
单线程下实现并发
我们程序员自己再代码层面上检测我们所有的IO操作
一旦遇到IO了 我们在代码级别完成切换
这样给CPU的感觉是你这个程序一直在运行 没有IO
从而提升程序的运行效率
多道技术
切换+保存状态
CPU两种切换
1.程序遇到IO
2.程序长时间占用
TCP服务端
accept
recv
代码如何做到
切换+保存状态
切换
切换不一定是提升效率 也有可能是降低效率
IO切 提升
没有IO切 降低
保存状态
保存上一次我执行的状态 下一次来接着上一次的操作继续往后执行
yield
"""
import time
# # 串行执行计算密集型的任务 1.2372429370880127
def func1():
for i in range(10000000):
i + 1
def func2():
for i in range(10000000):
i + 1
start_time = time.time()
func1()
func2()
print(time.time() - start_time)
# 切换 + yield 2.1247239112854004
import time

---

<!-- p.231 -->

11.18.2 gevent模块(了解)
def func1():
while True:
10000000 + 1
yield
def func2():
g = func1() # 先初始化出生成器
for i in range(10000000):
i + 1
next(g)
start_time = time.time()
func2()
print(time.time() - start_time)
pip3 install gevent
from gevent import monkey;monkey.patch_all()
import time
from gevent import spawn
"""
gevent模块本身无法检测常见的一些io操作
在使用的时候需要你额外的导入一句话
from gevent import monkey
monkey.patch_all()
又由于上面的两句话在使用gevent模块的时候是肯定要导入的
所以还支持简写
from gevent import monkey;monkey.patch_all()
"""
def heng():
print('哼')
time.sleep(2)
print('哼')
def ha():
print('哈')
time.sleep(3)
print('哈')
def heiheihei():
print('heiheihei')
time.sleep(5)
print('heiheihei')
start_time = time.time()
g1 = spawn(heng)
g2 = spawn(ha)
g3 = spawn(heiheihei)
g1.join()
g2.join() # 等待被检测的任务执行完毕 再往后继续执行
g3.join()

---

<!-- p.232 -->

11.18.3 协程实现TCP服务端的并发
# heng()
# ha()
# print(time.time() - start_time) # 5.005702018737793
print(time.time() - start_time) # 3.004199981689453 5.005439043045044
# 服务端
from gevent import monkey;monkey.patch_all()
import socket
from gevent import spawn
def communication(conn):
while True:
try:
data = conn.recv(1024)
if len(data) == 0: break
conn.send(data.upper())
except ConnectionResetError as e:
print(e)
break
conn.close()
def server(ip, port):
server = socket.socket()
server.bind((ip, port))
server.listen(5)
while True:
conn, addr = server.accept()
spawn(communication, conn)
if __name__ == '__main__':
g1 = spawn(server, '127.0.0.1', 8080)
g1.join()
# 客户端
from threading import Thread, current_thread
import socket
def x_client():
client = socket.socket()
client.connect(('127.0.0.1',8080))
n = 0
while True:
msg = '%s say hello %s'%(current_thread().name,n)
n += 1
client.send(msg.encode('utf-8'))
data = client.recv(1024)
print(data.decode('utf-8'))
if __name__ == '__main__':

---

<!-- p.233 -->

11.18.4 总结
11.19 IO模型
11.19.1 IO模型简介
11.19.2 阻塞IO模型
for i in range(500):
t = Thread(target=x_client)
t.start()
"""
理想状态:
我们可以通过
多进程下面开设多线程
多线程下面再开设协程序
从而使我们的程序执行效率提升
"""
"""
我们这里研究的IO模型都是针对网络IO的
Stevens在文章中一共比较了五种IO Model：
* blocking IO 阻塞IO
* nonblocking IO 非阻塞IO
* IO multiplexing IO多路复用
* signal driven IO 信号驱动IO
* asynchronous IO 异步IO
由signal driven IO（信号驱动IO）在实际中并不常用，所以主要介绍其余四种IO Model。
"""
#1）等待数据准备 (Waiting for the data to be ready)
#2）将数据从内核拷贝到进程中(Copying the data from the kernel to the process)
## 同步异步
## 阻塞非阻塞
## 常见的网络阻塞状态:
accept
recv
recvfrom
## send虽然它也有io行为 但是不在我们的考虑范围
"""
我们之前写的都是阻塞IO模型 协程除外
"""
import socket
server = socket.socket()
server.bind(('127.0.0.1',8080))
server.listen(5)
while True:

---

<!-- p.234 -->

11.19.3 非阻塞IO
conn, addr = server.accept()
while True:
try:
data = conn.recv(1024)
if len(data) == 0:break
print(data)
conn.send(data.upper())
except ConnectionResetError as e:
break
conn.close()
# 在服务端开设多进程或者多线程 进程池线程池 其实还是没有解决IO问题
## 该等的地方还是得等 没有规避
## 只不过多个人等待的彼此互不干扰
"""
要自己实现一个非阻塞IO模型
"""
import socket
import time
server = socket.socket()
server.bind(('127.0.0.1', 8081))
server.listen(5)
# 将所有的网络阻塞变为非阻塞
server.setblocking(False)
r_list = []
del_list = []
while True:
try:
conn, addr = server.accept()
r_list.append(conn)
except BlockingIOError:
# time.sleep(0.1)
# print('列表的长度:',len(r_list))
# print('做其他事')
for conn in r_list:
try:
data = conn.recv(1024) # 没有消息 报错
if len(data) == 0: # 客户端断开链接
conn.close() # 关闭conn
# 将无用的conn从r_list删除
del_list.remove(conn)
continue
conn.send(data.upper())
except BlockingIOError:
continue
except ConnectionResetError:
conn.close()
del_list.append(conn)
# 挥手无用的链接
for conn in del_list:
r_list.remove(conn)
del_list.clear()

---

<!-- p.235 -->

11.19.4 总结
11.19.5 IO多路复用
# 客户端
import socket
client = socket.socket()
client.connect(('127.0.0.1',8081))
while True:
client.send(b'hello world')
data = client.recv(1024)
print(data)
"""
虽然非阻塞IO给你的感觉非常的牛逼
但是该模型会 长时间占用着CPU并且不干活 让CPU不停的空转
我们实际应用中也不会考虑使用非阻塞IO模型
任何的技术点都有它存在的意义
实际应用或者是思想借鉴
"""
"""
当监管的对象只有一个的时候 其实IO多路复用连阻塞IO都比比不上！！！
但是IO多路复用可以一次性监管很多个对象
server = socket.socket()
conn,addr = server.accept()
监管机制是操作系统本身就有的 如果你想要用该监管机制(select)
需要你导入对应的select模块
"""
import socket
import select
server = socket.socket()
server.bind(('127.0.0.1',8080))
server.listen(5)
server.setblocking(False)
read_list = [server]
while True:
r_list, w_list, x_list = select.select(read_list, [], [])
"""
帮你监管
一旦有人来了 立刻给你返回对应的监管对象
"""
# print(res) # ([<socket.socket fd=3, family=AddressFamily.AF_INET,
type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 8080)>], [], [])

---

<!-- p.236 -->

11.19.6 总结
# print(server)
# print(r_list)
for i in r_list: #
"""针对不同的对象做不同的处理"""
if i is server:
conn, addr = i.accept()
# 也应该添加到监管的队列中
read_list.append(conn)
else:
res = i.recv(1024)
if len(res) == 0:
i.close()
# 将无效的监管对象 移除
read_list.remove(i)
continue
print(res)
i.send(b'heiheiheiheihei')
# 客户端
import socket
client = socket.socket()
client.connect(('127.0.0.1',8080))
while True:
client.send(b'hello world')
data = client.recv(1024)
print(data)
"""
监管机制其实有很多
select机制 windows linux都有
poll机制 只在linux有 poll和select都可以监管多个对象 但是poll监管的数量更多
上述select和poll机制其实都不是很完美 当监管的对象特别多的时候
可能会出现 极其大的延时响应
epoll机制 只在linux有
它给每一个监管对象都绑定一个回调机制
一旦有响应 回调机制立刻发起提醒
针对不同的操作系统还需要考虑不同检测机制 书写代码太多繁琐
有一个人能够根据你跑的平台的不同自动帮你选择对应的监管机制
selectors模块
"""

---

<!-- p.237 -->

11.19.7 异步IO
"""
异步IO模型是所有模型中效率最高的 也是使用最广泛的
相关的模块和框架
模块:asyncio模块
异步框架:sanic tronado twisted
速度快！！！
"""
import threading
import asyncio
@asyncio.coroutine
def hello():
print('hello world %s'%threading.current_thread())
yield from asyncio.sleep(1) # 换成真正的IO操作
print('hello world %s' % threading.current_thread())
loop = asyncio.get_event_loop()
tasks = [hello(),hello()]
loop.run_until_complete(asyncio.wait(tasks))
loop.close()

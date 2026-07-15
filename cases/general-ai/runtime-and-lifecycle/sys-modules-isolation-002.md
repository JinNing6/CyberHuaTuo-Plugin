---
id: general-ai-sys-modules-isolation-002
title: "单测独立通过但全量失败的 sys.modules 污染"
title_en: "Tests pass alone but fail together after sys.modules mutation"
framework: general-ai
framework_version: "Python 3.9+"
language: python
tags: [pytest, sys.modules, import-cache, test-isolation]
severity: high
complexity: complex
quality_status: reviewed
disease_category: runtime-and-lifecycle
case_origin: maintainer-incident
origin_skill: python-test-module-registry-isolation
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "tests pass alone fail together sys.modules"
  - "NameError typing get_type_hints sys.modules"
environment:
  python_version: ">=3.9"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://docs.python.org/3/reference/import.html#the-module-cache"
related_cases: []
---

## 症状描述

两个测试单独运行都通过，按完整收集顺序运行时却在 `typing.get_type_hints`、延迟注解或类身份比较处失败；常见报错是原本存在的类型名突然 `NameError`。

## 根因分析

`sys.modules` 是进程级可写模块缓存。较早的测试删除、替换或重载包模块后，后续测试仍持有旧类或函数对象，但模块注册表已指向另一个对象或缺失。注解解析会使用定义对象对应的模块命名空间，于是形成测试顺序依赖。

## 药方

优先把“验证轻量导入不会加载重依赖”的破坏性探针放进会自行退出的子进程。确实必须进程内测试时，在 `try/finally` 中保存并恢复每个受影响模块的**原对象**，同时恢复父包属性；不要整体替换 `sys.modules`，也不要为迁就测试而降低生产类型精度。

```python
result = subprocess.run(
    [sys.executable, "-c", probe],
    cwd=PROJECT_ROOT,
    text=True,
    capture_output=True,
    check=False,
)
assert result.returncode == 0, result.stderr
```

## 验证

先运行最小失败顺序，再运行完整测试套件；检查子进程自然退出且没有模块注册表状态泄漏。若必须进程内恢复，额外断言恢复后的 `sys.modules[name] is original_module`。本病例来自维护者既有故障复盘，本轮未重复运行原项目测试。

## 风险与回退

不要用 `importlib.reload` 掩盖旧对象问题，它可能制造第二套类身份。子进程探针若自身包含进程清理缺陷，应先修复清理边界，再采用该隔离方案。

## 参考资料

- https://docs.python.org/3/reference/import.html#the-module-cache

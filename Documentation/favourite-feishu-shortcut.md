# 收藏点 → 飞书 → 恢复真实位置

## 直接导入（无需逐项添加）

安装包含此功能的 WrapPin 后，先完成配对并保存至少一个收藏点。把对应文件通过 AirDrop 或 iCloud Drive 发送到 iPhone，打开并确认添加：

- 标准版：[WrapPin-Feishu.shortcut](../Shortcuts/WrapPin-Feishu.shortcut)
- 隧道版：[WrapPin-Tunnel-Feishu.shortcut](../Shortcuts/WrapPin-Tunnel-Feishu.shortcut)

文件已经通过 macOS `shortcuts sign --mode anyone` 签名。运行时会询问收藏点，后面的动作已配置好。需要安装飞书；如果重签 App 时修改了 Bundle ID，请使用下方脚本重新生成对应文件。签名成功不等于真机端到端验证；尚需确认 iPhone 能识别 App 动作并完成蜂窝和跨 App 操作。

## 用代码重新生成

```sh
python3 scripts/build-feishu-shortcut.py --sign
python3 scripts/build-feishu-shortcut.py --bundle-id com.suversal.wrappin.selfsigned --name 'WrapPin Tunnel' --output Shortcuts/WrapPin-Tunnel-Feishu.shortcut --sign
```

脚本只使用 Python 标准库和 macOS 自带的 `shortcuts` 命令。签名会将快捷指令文件发送给 Apple 验证，采用 `anyone` 模式，不嵌入个人联系人信息。旁边的 `.unsigned.shortcut` 是可审查的 XML 源文件，导入时请选择没有 `.unsigned` 的文件。

## 动作说明

如需手动调整，可在动作列表的「App → WrapPin」中找到两个新动作：

- **准备收藏点自动化**：参数为收藏点，可设为「每次询问」。最多等待 25 秒，返回是否需要关闭蜂窝数据。连接已经成功时返回「假」，无需关闭蜂窝。
- **等待收藏点模拟**：最多等待 25 秒，返回准备的收藏点是否模拟成功。连接失败、超时或找不到本次准备请求时返回「假」，不以抛出错误的方式中断后续开启蜂窝的动作。

## 动作顺序

1. **WrapPin：准备收藏点自动化**，选择收藏点或「每次询问」。
2. **如果**第 1 步的结果为真：
   - **设置蜂窝数据：关闭**。
3. **结束如果**。
4. **WrapPin：等待收藏点模拟**。
5. **设置蜂窝数据：开启**。这一项必须放在判断等待结果之前，且放在「如果」之外。
6. **如果**第 4 步的结果为真：
   - **打开 App：飞书**。
   - **等待：5 秒**。
7. **结束如果**。
8. **WrapPin：停止并恢复真实位置**。这一项也必须放在「如果」之外，确保连接失败时仍取消未完成的连接。

在第 6 步选择魔法变量时，明确选择「等待收藏点模拟」的结果，而不是「准备收藏点自动化」的结果。可以将这个组合快捷指令添加到主屏幕。

## 行为与边界

- WrapPin 的准备、等待和恢复动作会打开 WrapPin；最后一步因此会从飞书返回 WrapPin。
- 如果已经有模拟正在运行，准备动作会拒绝开始。请先停止已有模拟。
- 准备阶段超时或失败会取消本次连接并报错，此时还没有执行关闭蜂窝的动作。
- 蜂窝关闭后的等待失败会返回「假」；按上述配置，后续仍会开启蜂窝并停止模拟，不会打开飞书。
- 这个流程以蜂窝数据开启结束，不保存原来的蜂窝开关状态。
- 保持手机解锁。用户取消、系统终止快捷指令或 App 被终止时，后续动作不保证执行。遇到这种情况，手动开启蜂窝数据，并运行「停止并恢复真实位置」后再重试。
- 等待五秒只是停留时间，不表示飞书已经读取定位或完成任何业务操作。
- 首次使用隧道的系统授权，以及外部隧道 App 的交互，仍可能需要手动处理。

## 验证

开发侧可运行 `python3 scripts/test-shortcut-automation.py` 验证等待动作的成功、失败、超时、目标不匹配、已有会话和取消分支。模拟器构建可验证 App Intents 元数据；真正的蜂窝切换、外部隧道交接和跨 App 五秒后返回必须在已配对的 iPhone 上按上面的步骤验收。

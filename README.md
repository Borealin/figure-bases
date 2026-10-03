# figure-bases

自制 3D 打印手办底座：把原厂分开的底座合成一块、按自己想要的摆法重新排，省空间。
CadQuery 建模，Bambu Lab A1 mini 打印。

## 底座列表

| 系列 | 手办 | 文件夹 | 尺寸 | 状态 |
|---|---|---|---|---|
| POP UP PARADE | 東方仗助 × 岸辺露伴（『ジョジョの奇妙な冒険 ダイヤモンドは砕けない』） | [pop-up-parade/josuke-higashikata__rohan-kishibe](pop-up-parade/josuke-higashikata__rohan-kishibe) | 146 × 97 × 11mm | 已打印 |
| POP UP PARADE | 2B × A2（『NieR:Automata Ver1.1a』） | [pop-up-parade/2b__a2](pop-up-parade/2b__a2) | 128 × 144 × 11mm | 已打印 |

文件夹命名：`<系列>/<角色罗马音>__<角色罗马音>`，完整商品名写在各自的 README 里。

## 流程

1. **测量**：游标卡尺量每根脚钉的直径和露出长度，以及原厂底座上孔与孔的**近边距**。
   原厂是六边形孔时，中心距 ≈ 近边距 + (r1 + r2) × 1.05；圆孔直接加两个半径。
   数字卡尺没电时读数会整体偏小，而且彼此还自洽（2B × A2 那次只有真值一半），拿照片比例交叉核对一下。
   原厂底座上如果有放鞋跟的凹槽，要量它的形状和**深度**，深度不对会把鞋跟垫高。
2. **拍照**：空底座正上方俯拍（确定孔位的左右 / 镜像方向），再拍手办正面（确定朝向和重心）。
3. **公差条 + 验证垫块**：每只脚一个比鞋底还小的垫块，两个手办能贴多近都不会被垫块挡住。
4. **试摆**：垫块粘在垫子上摆出想要的效果，拔下手办，量 3～4 个跨手办的孔距，
   用最小二乘解出两个手办的相对位置。每个手办只有两个孔时距离解不出镜像，要对照实物确认。
5. **试摆底座（可选）**：薄底板 + 桩，省料，确认摆位和重心。
6. **正式底座**：实心整板，孔直接开在板上。

经验参数（A1 mini + Bambu PLA Basic + 0.20mm Standard）：

- 六边形孔对边距 ≈ 钉径（**不加间隙**；+0.2 已明显偏松），个别孔 ±0.03 微调，2B × A2 那套最后整体再 ×1.01
- 孔深 = 钉长 + 1.5mm，孔口 0.4mm 倒角
- 鞋跟凹槽每边放大 0.3～0.5mm，深度照原厂
- 底座厚 11mm；POP UP PARADE 的钉露出 6.6～7.7mm，孔底还剩约 1.8mm

## 工具

| 文件 | 用途 |
|---|---|
| `tools/heic2jpg.py` | iPhone HEIC 照片转 JPG（ffmpeg 拼回分块网格） |
| `tools/slice_a1mini.ps1` | 用 Bambu Studio 命令行切片，输出可直接打印的 `.3mf` |
| `tools/flatten_preset.py` | 展开 Bambu 系统预设的继承链（命令行不会自己展开，否则用的是默认参数） |
| `tools/render.py` | 只依赖 numpy 的简易渲染器，给 README 出预览图 |

## 环境

- Python 3.10+，`pip install -r requirements.txt`（CadQuery）
  - Windows：CadQuery 的 OCP DLL 放在太深的路径下会报"文件名或扩展名太长"，要装在短路径里（或用 `subst` 映射一个短盘符）
- ffmpeg（转换照片）
- Bambu Studio（切片，默认装在 `C:\Program Files\Bambu Studio`）

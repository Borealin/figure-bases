# figure-bases

自制 3D 打印手办底座：把原厂分开的底座合成一块、按自己想要的摆法重新排，省空间。
CadQuery 建模，Bambu Lab A1 mini 打印。

## 底座列表

| 系列 | 手办 | 文件夹 | 摆法 | 尺寸 | 状态 |
|---|---|---|---|---|---|
| POP UP PARADE | 東方仗助 × 岸辺露伴（『ジョジョの奇妙な冒険 ダイヤモンドは砕けない』） | [josuke-higashikata__rohan-kishibe](pop-up-parade/josuke-higashikata__rohan-kishibe) | 交叠 | 146 × 97 | 已打印 |
| POP UP PARADE | 2B × A2（『NieR:Automata Ver1.1a』） | [2b__a2](pop-up-parade/2b__a2) | L 形 | 128 × 144 | 已打印 |
| POP UP PARADE | Panty & Stocking Set（『Panty & Stocking with Garterbelt』） | [panty__stocking](pop-up-parade/panty__stocking) | 背靠背 | 110 × 130 | 已打印 |
| POP UP PARADE | Panty & Stocking Set: Repent Ver. L Size | [panty__stocking_repent](pop-up-parade/panty__stocking_repent) | 并排 | 103 × 104 | 已打印 |
| POP UP PARADE | Byleth (Male) × Byleth (Female)（『Fire Emblem: Three Houses』） | [byleth-male__byleth-female](pop-up-parade/byleth-male__byleth-female) | 并排 | 153 × 157 | 已打印 |
| POP UP PARADE SP | Wise × Belle（『Zenless Zone Zero』） | [wise__belle](pop-up-parade/wise__belle) | 并排 | 77 × 103 | 已打印，W2 放大重打 |

尺寸单位 mm，厚度都是 11mm。所有正式底座都刻了手办名字，防止几套搞混。
文件夹命名：`<系列>/<角色罗马音>__<角色罗马音>`，完整商品名写在各自的 README 里。

`plates/` 放几套拼在一起的打印盘（`plate_test_*` 是试摆盘，`plate_fit-samples_*` 是孔径试样）。

## 流程

1. **测量**：游标卡尺量每根脚钉的直径和露出长度，以及原厂底座上孔与孔的距离（近边距，或者圆周上的最远距离）。
   原厂是六边形孔时，中心距 ≈ 近边距 + (r1 + r2) × 1.05；圆孔直接加两个半径。
   数字卡尺没电时读数会整体偏小，而且彼此还自洽（2B × A2 那次只有真值一半），拿照片比例交叉核对一下。
   原厂底座上如果有放鞋跟的凹槽，要量它的形状和**深度**，深度不对会把鞋跟垫高。
2. **拍照**：空底座正上方俯拍（定孔位的左右 / 镜像方向，也用来推手办朝向），再拍手办正面。
3. **验证垫块 + 孔径试样**：每只脚一个比鞋底还小的垫块，两个手办能贴多近都不会被垫块挡住。
   - 垫块的孔按实测钉径（100%）开；同一波另出 96 / 98 / 100 / 102 / 104% 五档孔径试样，对比着试松紧
   - 每根钉一组圆柱试样；同一套里几根钉粗细接近时，改成一根公差条（一行一根钉 × 五档）更省
   - 几套可以一次量完、垫块和试样拼一盘打（见 `plates/`）
4. **试摆**：垫块粘在垫子上摆出想要的效果，拔下手办，量跨手办的孔边距离，用最小二乘解出相对位置。
   - 近边距按六边形外接圆半径换算成中心距，拟合后有比实测近的就整体往外推——**宁远勿近**
   - 每人只有两个孔时距离解不出镜像：给出"正面看从左到右的孔顺序"，再结合原厂底座俯拍推出的朝向就能定
   - 多量几条有冗余，记错的数（比如 104.9 / 114.9）能交叉检查出来
5. **试摆底座**：0.8mm 薄底板 + 每孔一个桩 + 加强筋 + 凸字，省料，确认摆位、朝向和重心。
6. **正式底座**：11mm 实心整板 + 刻字。外轮廓包住所有孔和原厂底座中心周围 15mm（保证重心在底座内），再留 10mm 边。

经验参数（A1 mini + Bambu PLA Basic + 0.20mm Standard）：

- 六边形孔对边距 ≈ 钉径 × 1.00 ～ 1.01，同一批钉松紧差别也不小，所以第一波就出五档试样
- 试装后要调粗细时**不要一步调满**：0.1mm 的差别手感就很明显（Panty × Stocking 的 P1 是 5.2 偏松、5.1 偏紧、5.12 刚好），
  觉得松就在试过的孔上 −2%、紧就 +2% 出圆柱试样，试完再定。
  天使版 Panty × Stocking、贝雷特、哲 × 铃三套最后定的孔都在垫块孔的 −2% ～ +2% 之间，折合实测钉径的 99% ～ 103%，大多数就是 100%
- 孔深 = 钉长 + 1.5mm，孔口 0.4mm 倒角；底座 11mm 厚，钉最长 8.5mm 时孔底还剩 1mm
- 鞋跟凹槽每边放大 0.3～0.5mm，深度照原厂

## 工具

| 文件 | 用途 |
|---|---|
| `tools/fit_samples.py` | 孔径试样：圆柱试样（帽子形，一档一个）、公差条、五档 / ±2% 档位计算 |
| `tools/basekit.py` | 两组孔的摆放求解（含宁远勿近外推）、朝向 / 左右顺序核对、外轮廓、底座建模、自动找位置刻字 |
| `tools/base_preview.py` | 底座预览图：平台上的俯视图（孔、原厂底座中心、手办朝向）+ 立体图 |
| `tools/heic2jpg.py` | iPhone HEIC 照片转 JPG（ffmpeg 拼回分块网格） |
| `tools/slice_a1mini.ps1` | 用 Bambu Studio 命令行切片，输出可直接打印的 `.3mf`；`-Stl a.stl,b.stl` 多个模型拼一盘 |
| `tools/flatten_preset.py` | 展开 Bambu 系统预设的继承链（命令行不会自己展开，否则用的是默认参数） |
| `tools/render.py` | 只依赖 numpy 的简易渲染器，给 README 出预览图 |

## 环境

- Python 3.10+，`pip install -r requirements.txt`（CadQuery）
  - Windows：CadQuery 的 OCP DLL 放在太深的路径下会报"文件名或扩展名太长"，要装在短路径里，
    例如 `pip install --target cqlib cadquery`，运行前设 `PYTHONPATH=<仓库>/cqlib`（`cqlib/` 已在 .gitignore 里）
- ffmpeg（转换照片）
- Bambu Studio（切片，默认装在 `C:\Program Files\Bambu Studio`）

# 营养知识库来源

以下资料用于估算照片打卡营养。条目保留来源编号、名称、检索别名和能量、蛋白质、脂肪、碳水四项。每 100 克对应食品可食部分。每份对应原研究配方的份量。

| 文件 | 条目 | 计量 | 来源与许可 |
| --- | ---: | --- | --- |
| `tfda_foods.csv` | 2,160 | 每 100 克 | 衛生福利部食品藥物管理署，食品營養成分資料集。[资料来源](https://data.gov.tw/dataset/8543) · [政府資料開放授權條款第 1 版](https://data.gov.tw/license) |
| `chinese_recipes.csv` | 3,089 | 参考配方每份 | Long 等，3,302 道中式配方营养、环境与经济评估，Figshare v2。[资料来源](https://doi.org/10.6084/m9.figshare.29977027.v2) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `sichuan_cantonese_recipes.csv` | 997 | 参考配方每份 | Long 等，1,000 道川菜与粤菜的环境足迹和营养摄入，Figshare v4。[资料来源](https://doi.org/10.6084/m9.figshare.28457018.v4) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| `usda_sr_legacy.csv` | 34 | 每 100 克 | USDA Agricultural Research Service，FoodData Central SR Legacy，2018-04。[资料来源](https://fdc.nal.usda.gov/download-datasets/) · [CC0 许可](https://fdc.nal.usda.gov/api-guide/#licensing) |

食药署数据保留四项数值齐全的样品，并补充简繁体和少量常用别名。六大菜系表取原始每份数据，川菜和粤菜表用整份配方的营养值除以来源的份数。菜谱表剔除了能量与蛋白质、脂肪明显不一致的记录。川菜和粤菜的条目主要使用英文名称，其中部分常见菜另外标有中文别名。同名配方可能有不同做法，保留为独立记录。

## 重新生成中文数据

下载[食药署 CSV 压缩包](https://data.fda.gov.tw/data/opendata/export/20/csv)、[六大菜系营养表](https://figshare.com/ndownloader/files/57756373)、[川菜表](https://figshare.com/ndownloader/files/55558094)和[粤菜表](https://figshare.com/ndownloader/files/55558097)。在 `backend` 目录执行以下命令，把参数替换为你下载的文件路径。运行服务时直接读取生成的 CSV。

```powershell
uv run --with opencc-python-reimplemented==0.1.7 --with 'openpyxl>=3.1,<4' python data/import_chinese_nutrition.py --tfda tfda.zip --six-cuisines six-cuisines.xlsx --sichuan sichuan.xlsx --cantonese cantonese.xlsx
```

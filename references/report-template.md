# 中文报告模板

```markdown
# 抗原筛选报告

## 候选输入概况
- 输入来源：
- 候选数量：
- 物种：
- 目标 modality：
- 本次是否联网：
- 使用证据：

## 通过 / 失败 / 不确定靶点
| 分类 | 候选 | 主要原因 | 缺失证据 |
|---|---|---|---|
| 通过 | | | |
| 条件通过 | | | |
| 失败 | | | |
| 不确定 | | | |

## Modality-Specific 结论
| 候选 | antibody | CAR-T | ADC | bispecific | soluble ECD screen |
|---|---|---|---|---|---|

## ECD Construct 方案
| 候选 | ECD 边界 | 推荐 construct | 标签/展示 | QC |
|---|---|---|---|---|

## 风险 Flags
- 正常组织风险：
- isoform / topology 风险：
- modality 风险：
- construct 风险：

## 缺失证据
- topology：
- ECD boundary：
- human-mouse ECD identity：
- normal tissue：
- drug / clinical / preclinical：

## Fixture smoke 说明
- 本报告如果来自 fixture smoke test，只代表 pipeline triage / engineering validation。
- 如使用本地 `ECD_identity`，必须记录 provenance；`seq_identity` 不用于 mouse-model gate。
- HPA/GTEx、Open Targets/ChEMBL、Ensembl/MGI live adapters 若未运行，必须标记为 pending/missing。

## 下一步实验建议
1. 补充 surface protein evidence，例如 flow、surface proteomics 或 IF/IHC 定位。
2. 对条件通过候选验证 ECD construct 表达、SEC、还原/非还原胶和 binding QC。
3. 若要做小鼠模型，补充人鼠 ECD identity 和交叉反应实验。
```

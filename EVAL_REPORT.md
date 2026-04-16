# mdrag Evaluation Report

- Top-K: **5**
- Queries: **15**
- Indexes compared: `vector` (vector), `bm25` (bm25), `hybrid` (hybrid)

## Overall

| Metric | vector | bm25 | hybrid |
|---|---|---|---|
| Recall@5 | 80.0% (12/15) | 93.3% (14/15) | 100.0% (15/15) |
| MRR | 0.644 | 0.817 | 0.819 |

## Subset: `general` (5 queries)

| Metric | vector | bm25 | hybrid |
|---|---|---|---|
| Recall@5 | 80.0% (4/5) | 80.0% (4/5) | 100.0% (5/5) |
| MRR | 0.533 | 0.650 | 0.557 |

## Subset: `needle` (10 queries)

| Metric | vector | bm25 | hybrid |
|---|---|---|---|
| Recall@5 | 80.0% (8/10) | 100.0% (10/10) | 100.0% (10/10) |
| MRR | 0.700 | 0.900 | 0.950 |

## Per-Query Results

Rank shown is the position of the first expected document (— = not in top-K).

| # | Kind | Query | vector rank | bm25 rank | hybrid rank |
|---|---|---|---|---|---|
| 1 | general | 明道云核心功能介绍 | — | ✅ #1 | ✅ #3 |
| 2 | general | nocoly 合作伙伴计划 | ✅ #3 | — | ✅ #5 |
| 3 | general | HAP 产品与低代码平台的区别 | ✅ #1 | ✅ #1 | ✅ #1 |
| 4 | general | 华夏银行 项目案例 | ✅ #1 | ✅ #1 | ✅ #1 |
| 5 | general | 数字化转型制造业案例 | ✅ #3 | ✅ #4 | ✅ #4 |
| 6 | needle | 郑州日产项目协作效率提升多少百分比 | ✅ #2 | ✅ #2 | ✅ #2 |
| 7 | needle | HAP 如何解决加盟商全生命周期管理的痛点 | — | ✅ #1 | ✅ #1 |
| 8 | needle | 南京青扬 RFID 标签在仓储中的具体应用 | ✅ #1 | ✅ #1 | ✅ #1 |
| 9 | needle | 郑州日产零代码文化推广的三个阶段 | ✅ #2 | ✅ #1 | ✅ #1 |
| 10 | needle | 医药行业 AI 成熟度分级的第五阶段定义 | ✅ #1 | ✅ #1 | ✅ #1 |
| 11 | needle | 红菱混合系统核心功能模块 OA ERP RPA 集成 | ✅ #1 | ✅ #1 | ✅ #1 |
| 12 | needle | 明道云 38 种字段控件类型易用性设计 | — | ✅ #1 | ✅ #1 |
| 13 | needle | 华夏银行 i 助手平台部署了多少个应用 | ✅ #1 | ✅ #1 | ✅ #1 |
| 14 | needle | MPC2025 武测空间无人机日均飞行架次数量 | ✅ #1 | ✅ #1 | ✅ #1 |
| 15 | needle | Nocoly HAP vs Outsystems builder accessibility differences | ✅ #1 | ✅ #2 | ✅ #1 |

## Expected vs. Returned


### Q1. 明道云核心功能介绍

- **Kind:** general
- **Expected:** `mingdao/intro/明道云伙伴introbook.md`, `mingdao/intro/明道云特性清单.md`
- **vector** (rank: —):
  1.    `mingdao/cases/mpc2025/西安云开信息技术有限公司-明道云在突发事件现场态势感知的应用.md`
  2.    `mingdao/cases/open-day/作业帮-作业帮基于明道云开展的硬件业务数字化建设.md`
  3.    `mingdao/cases/mpc2023/苏州睿能科技有限公司-集成开发之如何用好明道云.md`
  4.    `mingdao/伙伴企微群/伙伴能力图谱.md`
  5.    `mingdao/cases/mpc2023/北京戴斯克商务有限公司-明道云在戴斯克从业务整合到高效管理的秘诀.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/intro/明道云伙伴introbook.md`
  2.    `mingdao/live-series/2024/hap-0180-HAP实战直播第180期打造企业因公收支与金融解决方案明道云与支付宝企.md`
  3.    `mingdao/live-series/2024/hap-0171-HAP实战直播第171期打造企业智能客服系统明道云与帮我吧合作场景介绍.md`
  4.    `mingdao/live-series/2022/zls-0111-零代码实践第111期-明道云-V75-版本新功能介绍.md`
  5.    `mingdao/live-series/2025/hap-0255-HAP实战直播第255期AI赋能HAP从需求解析到应用优化的全链路实践.md`
- **hybrid** (rank: 3):
  1.    `mingdao/cases/mpc2025/西安云开信息技术有限公司-明道云在突发事件现场态势感知的应用.md`
  2.    `mingdao/cases/open-day/作业帮-作业帮基于明道云开展的硬件业务数字化建设.md`
  3. 👉 `mingdao/intro/明道云伙伴introbook.md`
  4.    `mingdao/live-series/2024/hap-0180-HAP实战直播第180期打造企业因公收支与金融解决方案明道云与支付宝企.md`
  5.    `mingdao/cases/mpc2023/苏州睿能科技有限公司-集成开发之如何用好明道云.md`

### Q2. nocoly 合作伙伴计划

- **Kind:** general
- **Expected:** `nocoly/intro/02_partner-program/Nocoly Partnership Essentials.md`
- **vector** (rank: 3):
  1.    `nocoly/intro/03_product-sales-enablement/FAQ of Nocoly Sales Activity.md`
  2.    `nocoly/intro/02_partner-program/Nocoly Partnership Agreement.md`
  3. 👉 `nocoly/intro/02_partner-program/Nocoly Partnership Essentials.md`
  4.    `nocoly/intro/05_case-studies/account/中银香港 (Bank of China, Hong Kong).md`
  5.    `nocoly/intro/02_partner-program/A full explainer of Nocoly's VAR Partnership.md`
- **bm25** (rank: —):
  1.    `nocoly/intro/03_product-sales-enablement/FAQ of Nocoly Sales Activity.md`
  2.    `nocoly/intro/_蒸馏洞察.md`
  3.    `mingdao/intro/明道云伙伴introbook.md`
  4.    `nocoly/intro/05_case-studies/_蒸馏洞察.md`
  5.    `mingdao/intro/明道云合作伙伴政策细节和常见问答.md`
- **hybrid** (rank: 5):
  1.    `nocoly/intro/03_product-sales-enablement/FAQ of Nocoly Sales Activity.md`
  2.    `nocoly/intro/_蒸馏洞察.md`
  3.    `nocoly/intro/02_partner-program/Nocoly Partnership Agreement.md`
  4.    `mingdao/intro/明道云伙伴introbook.md`
  5. 👉 `nocoly/intro/02_partner-program/Nocoly Partnership Essentials.md`

### Q3. HAP 产品与低代码平台的区别

- **Kind:** general
- **Expected:** `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`, `mingdao/intro/主流零代码平台分析报告.md`
- **vector** (rank: 1):
  1. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  2.    `mingdao/live-series/2025/hap-0239-HAP实战直播第239期小应用大作用基于HAP打造企业级数字化名片小程.md`
  3.    `mingdao/live-series/2025/hap-0251-HAP实战直播第251期研发设计协同新模式HAP驱动PLM创新升级.md`
  4.    `mingdao/cases/mpc2024/Catomind-Lim-从本地成功到国际拓展启舵科技与-HAP-的战略合作.md`
  5.    `mingdao/live-series/2024/hap-0178-HAP实战直播第178期明道云在医疗卫生行业的展业实践分享.md`
- **bm25** (rank: 1):
  1. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  2.    `mingdao/live-series/2024/hap-0178-HAP实战直播第178期明道云在医疗卫生行业的展业实践分享.md`
  3.    `mingdao/cases/mpc2025/深圳市深汕特别合作区智慧-从自我提升到城市进阶低代码与大模型的融合实践.md`
  4.    `mingdao/cases/all-hands-on/福州汉思信息技术有限公司-以卫浴行业为例介绍HAP平台在制造业MOM的应用.md`
  5.    `mingdao/cases/mpc2025/上海安丽锘云计算技术有限-从SAP、Salesforce走向HAP.md`
- **hybrid** (rank: 1):
  1. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  2.    `mingdao/cases/mpc2025/江苏九龙珠品牌管理股份有-花小钱办大事饮品连锁的-HAP-应用落地与成效.md`
  3.    `mingdao/live-series/2024/hap-0178-HAP实战直播第178期明道云在医疗卫生行业的展业实践分享.md`
  4.    `mingdao/live-series/2025/hap-0251-HAP实战直播第251期研发设计协同新模式HAP驱动PLM创新升级.md`
  5.    `mingdao/cases/all-hands-on/福州汉思信息技术有限公司-以卫浴行业为例介绍HAP平台在制造业MOM的应用.md`

### Q4. 华夏银行 项目案例

- **Kind:** general
- **Expected:** `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/线索表单/伙伴申请-线索.md`
  3.    `nocoly/intro/05_case-studies/account/中银香港 (Bank of China, Hong Kong).md`
  4.    `mingdao/intro/_蒸馏洞察.md`
  5.    `mingdao/intro/明道云HAP introbook.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/cases/open-day/_蒸馏洞察.md`
  3.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`
  4.    `mingdao/live-series/2020/zls-0035-零代码实践第35期国药福芯如何实现养老产业智慧化管理.md`
  5.    `mingdao/销售跟进日志/_蒸馏洞察.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/cases/open-day/_蒸馏洞察.md`
  3.    `mingdao/线索表单/伙伴申请-线索.md`
  4.    `nocoly/intro/05_case-studies/account/中银香港 (Bank of China, Hong Kong).md`
  5.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`

### Q5. 数字化转型制造业案例

- **Kind:** general
- **Expected:** `mingdao/cases/all-hands-on/深圳明道智远信息技术有限-从代码围城到零代码突围制造业数字化改造的转型实践.md`, `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
- **vector** (rank: 3):
  1.    `mingdao/live-series/2025/hap-0223-HAP实战直播第223期外贸型制造业数字化管理应用.md`
  2.    `mingdao/cases/mpc2024/上海橙木智能科技有限公司-制造业数字化演进历程中的创新与HAP-赋能.md`
  3. 👉 `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  4.    `mingdao/cases/all-hands-on/株洲畅快软件开发有限公司-小型离散制造企业低成本数字化破局之路与实战秘籍.md`
  5.    `mingdao/cases/all-hands-on/浙江春晖集团有限公司-传统制造业数字化转型60年老牌企业的破局经验与未来布局.md`
- **bm25** (rank: 4):
  1.    `mingdao/cases/mpc2024/上海橙木智能科技有限公司-制造业数字化演进历程中的创新与HAP-赋能.md`
  2.    `mingdao/cases/all-hands-on/株洲畅快软件开发有限公司-小型离散制造企业低成本数字化破局之路与实战秘籍.md`
  3.    `mingdao/live-series/2025/hap-0223-HAP实战直播第223期外贸型制造业数字化管理应用.md`
  4. 👉 `mingdao/cases/all-hands-on/深圳明道智远信息技术有限-从代码围城到零代码突围制造业数字化改造的转型实践.md`
  5.    `mingdao/cases/all-hands-on/上海电气集团数字科技有限-填补制造业数字化转型的‘最后一公里’从技术到落地的无缝衔接.md`
- **hybrid** (rank: 4):
  1.    `mingdao/live-series/2025/hap-0223-HAP实战直播第223期外贸型制造业数字化管理应用.md`
  2.    `mingdao/cases/mpc2024/上海橙木智能科技有限公司-制造业数字化演进历程中的创新与HAP-赋能.md`
  3.    `mingdao/cases/all-hands-on/株洲畅快软件开发有限公司-小型离散制造企业低成本数字化破局之路与实战秘籍.md`
  4. 👉 `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  5. 👉 `mingdao/cases/all-hands-on/深圳明道智远信息技术有限-从代码围城到零代码突围制造业数字化改造的转型实践.md`

### Q6. 郑州日产项目协作效率提升多少百分比

- **Kind:** needle
- **Expected:** `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
- **vector** (rank: 2):
  1.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  3.    `mingdao/cases/all-hands-on/衣星科技广州有限责任-高效汇聚协同创新——生产制造业数字化转型之路.md`
  4.    `nocoly/intro/05_case-studies/partners/fujifilm/FBHK_Nocoly_Partner_Case_Study.md`
  5.    `mingdao/cases/mpc2025/北京发那科机电有限公司-从数控到智控明道云与发那科的协同创新之路.md`
- **bm25** (rank: 2):
  1.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  3.    `mingdao/intro/明道云伙伴introbook.md`
  4.    `mingdao/intro/明道云零代码可行性分析报告.md`
  5.    `mingdao/cases/all-hands-on/福州汉思信息技术有限公司-世界在割裂工厂在融合汉思用HAP连接设备和未来.md`
- **hybrid** (rank: 2):
  1.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  3.    `mingdao/cases/all-hands-on/衣星科技广州有限责任-高效汇聚协同创新——生产制造业数字化转型之路.md`
  4.    `mingdao/intro/明道云零代码可行性分析报告.md`
  5.    `mingdao/intro/明道云伙伴introbook.md`

### Q7. HAP 如何解决加盟商全生命周期管理的痛点

- **Kind:** needle
- **Expected:** `mingdao/cases/mpc2025/谷连天餐饮管理有限公司-为什么选择HAP连锁餐饮企业的数字化实践.md`
- **vector** (rank: —):
  1.    `mingdao/live-series/2025/hap-0236-HAP实战直播第236期泛生活服务类机构会员运营一站式解决方案.md`
  2.    `mingdao/live-series/2025/hap-0253-HAP实战直播第253期HAP综合解决方案降本增效重塑数字化竞争力.md`
  3.    `mingdao/live-series/2024/hap-0215-HAP实战直播第215期劳动密集型企业复合用工数字化解决方案.md`
  4.    `mingdao/live-series/2024/hap-0193-HAP实战直播第193期如何通过HAP构建IOT车联网解决方案.md`
  5.    `mingdao/cases/mpc2024/上海汉得信息技术股份有限-实施模式变革汉得实施HAP的最佳实践.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/谷连天餐饮管理有限公司-为什么选择HAP连锁餐饮企业的数字化实践.md`
  2.    `mingdao/cases/mpc2025/江苏九龙珠品牌管理股份有-花小钱办大事饮品连锁的-HAP-应用落地与成效.md`
  3.    `mingdao/live-series/2025/hap-0227-HAP实战直播第227期打造智能设备管理系统零代码赋能点检到全生命周期.md`
  4.    `mingdao/live-series/2024/hap-0215-HAP实战直播第215期劳动密集型企业复合用工数字化解决方案.md`
  5.    `mingdao/live-series/2024/hap-0178-HAP实战直播第178期明道云在医疗卫生行业的展业实践分享.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/谷连天餐饮管理有限公司-为什么选择HAP连锁餐饮企业的数字化实践.md`
  2.    `mingdao/live-series/2025/hap-0236-HAP实战直播第236期泛生活服务类机构会员运营一站式解决方案.md`
  3.    `mingdao/cases/mpc2025/江苏九龙珠品牌管理股份有-花小钱办大事饮品连锁的-HAP-应用落地与成效.md`
  4.    `mingdao/live-series/2025/hap-0253-HAP实战直播第253期HAP综合解决方案降本增效重塑数字化竞争力.md`
  5.    `mingdao/live-series/2024/hap-0215-HAP实战直播第215期劳动密集型企业复合用工数字化解决方案.md`

### Q8. 南京青扬 RFID 标签在仓储中的具体应用

- **Kind:** needle
- **Expected:** `mingdao/cases/mpc2025/南京青扬智能科技有限公司-重塑制造业服务模式HAP-集成与扩展的价值探索.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/南京青扬智能科技有限公司-重塑制造业服务模式HAP-集成与扩展的价值探索.md`
  2.    `mingdao/线索表单/联系明道云销售-线索.md`
  3.    `mingdao/cases/all-hands-on/_蒸馏洞察.md`
  4.    `mingdao/销售跟进日志/日志_20260414101136.md`
  5.    `mingdao/线索表单/明道云私有部署咨询-线索.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/南京青扬智能科技有限公司-重塑制造业服务模式HAP-集成与扩展的价值探索.md`
  2.    `mingdao/live-series/2025/hap-0224-HAP实战直播第224期明道云在制造业MES场景的优势.md`
  3.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  4.    `mingdao/伙伴企微群/20250527-20251201.md`
  5.    `mingdao/live-series/2025/hap-0258-HAP实战直播第258期光伏行业数字化管理方案流程、仓储与结算的全链路.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/南京青扬智能科技有限公司-重塑制造业服务模式HAP-集成与扩展的价值探索.md`
  2.    `mingdao/线索表单/联系明道云销售-线索.md`
  3.    `mingdao/live-series/2025/hap-0224-HAP实战直播第224期明道云在制造业MES场景的优势.md`
  4.    `mingdao/cases/all-hands-on/_蒸馏洞察.md`
  5.    `mingdao/伙伴企微群/20250527-20251201.md`

### Q9. 郑州日产零代码文化推广的三个阶段

- **Kind:** needle
- **Expected:** `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
- **vector** (rank: 2):
  1.    `mingdao/live-series/2022/zls-0085-零代码实践第85期天津商业大学低代码平台建设实践.md`
  2. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  3.    `mingdao/live-series/2022/zls-0122-零代码实践第122期天津钢管用零代码突破传统思路重塑企业IT价值.md`
  4.    `mingdao/live-series/2021/zls-0041-零代码实践第41期使用零代码重构学校选课系统产品.md`
  5.    `mingdao/live-series/2022/zls-0094-零代码实践第94期明道云助力疫情防控排查高效解决排查难题.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  2.    `mingdao/live-series/2022/zls-0109-零代码实践第109期All-In-One的生产管理系统.md`
  3.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`
  4.    `mingdao/cases/all-hands-on/广州昱丰信息科技有限公司-打造分布式架构全球化ERPAI+零代码重构业务创新范式.md`
  5.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/郑州日产汽车有限公司-低代码平台助力汽车企业数字化转型.md`
  2.    `mingdao/live-series/2022/zls-0085-零代码实践第85期天津商业大学低代码平台建设实践.md`
  3.    `mingdao/live-series/2022/zls-0109-零代码实践第109期All-In-One的生产管理系统.md`
  4.    `mingdao/live-series/2022/zls-0122-零代码实践第122期天津钢管用零代码突破传统思路重塑企业IT价值.md`
  5.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`

### Q10. 医药行业 AI 成熟度分级的第五阶段定义

- **Kind:** needle
- **Expected:** `mingdao/cases/all-hands-on/连云港木杉医药科技有限公-AI驱动医药变革成熟度分级与创新应用.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/连云港木杉医药科技有限公-AI驱动医药变革成熟度分级与创新应用.md`
  2.    `mingdao/live-series/_蒸馏洞察.md`
  3.    `mingdao/live-series/2025/hap-0246-HAP实战直播第246期AI驱动的新一代全链路智能企业管理方案.md`
  4.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  5.    `mingdao/销售跟进日志/_蒸馏洞察.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/连云港木杉医药科技有限公-AI驱动医药变革成熟度分级与创新应用.md`
  2.    `mingdao/live-series/_蒸馏洞察.md`
  3.    `mingdao/cases/all-hands-on/_蒸馏洞察.md`
  4.    `mingdao/销售跟进日志/_蒸馏洞察.md`
  5.    `mingdao/cases/all-hands-on/复旦大学附属中山医院-零代码“智”变解锁医院敏捷化的金钥匙.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/连云港木杉医药科技有限公-AI驱动医药变革成熟度分级与创新应用.md`
  2.    `mingdao/live-series/_蒸馏洞察.md`
  3.    `mingdao/live-series/2025/hap-0246-HAP实战直播第246期AI驱动的新一代全链路智能企业管理方案.md`
  4.    `mingdao/cases/all-hands-on/_蒸馏洞察.md`
  5.    `mingdao/销售跟进日志/_蒸馏洞察.md`

### Q11. 红菱混合系统核心功能模块 OA ERP RPA 集成

- **Kind:** needle
- **Expected:** `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  2.    `mingdao/live-series/2023/zls-0159-零代码实践第159期RPA+零代码助力企业超自动化发展.md`
  3.    `mingdao/cases/all-hands-on/广州昱丰信息科技有限公司-打造分布式架构全球化ERPAI+零代码重构业务创新范式.md`
  4.    `mingdao/live-series/2025/hap-0251-HAP实战直播第251期研发设计协同新模式HAP驱动PLM创新升级.md`
  5.    `mingdao/intro/明道云HAP introbook.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  2.    `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-道阻且长行则将至-复合型中小制造业数字化自由的探索.md`
  3.    `mingdao/cases/mpc2025/广州红菱电热设备有限公司-我命由我不由天我的系统我做主-红菱的数智化自由之路.md`
  4.    `mingdao/cases/mpc2025/_蒸馏洞察.md`
  5.    `mingdao/live-series/2022/zls-0109-零代码实践第109期All-In-One的生产管理系统.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  2.    `mingdao/live-series/2023/zls-0159-零代码实践第159期RPA+零代码助力企业超自动化发展.md`
  3.    `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-道阻且长行则将至-复合型中小制造业数字化自由的探索.md`
  4.    `mingdao/cases/all-hands-on/广州昱丰信息科技有限公司-打造分布式架构全球化ERPAI+零代码重构业务创新范式.md`
  5.    `mingdao/live-series/2025/hap-0251-HAP实战直播第251期研发设计协同新模式HAP驱动PLM创新升级.md`

### Q12. 明道云 38 种字段控件类型易用性设计

- **Kind:** needle
- **Expected:** `mingdao/intro/主流零代码平台分析报告.md`
- **vector** (rank: —):
  1.    `mingdao/伙伴企微群/伙伴能力图谱.md`
  2.    `mingdao/live-series/2023/zls-0156-零代码实践第156期利用明道云实现自定义数据打印功能.md`
  3.    `mingdao/cases/mpc2024/广州艾空网络科技有限公司-让零代码系统界面体验更优秀.md`
  4.    `mingdao/cases/mpc2023/广州市衣湛国际信息科技有-零代码助力服装行业数字化转型.md`
  5.    `mingdao/live-series/2023/zls-0136-零代码实践第136期APaaS+数字孪生明道云与山海鲸联合方案.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/intro/主流零代码平台分析报告.md`
  2.    `mingdao/intro/明道云特性清单.md`
  3.    `mingdao/intro/_蒸馏洞察.md`
  4.    `mingdao/live-series/2024/hap-0203-HAP实战直播第203期如何让明道云搭建的界面更好看.md`
  5.    `mingdao/live-series/2023/hap-0169-HAP实战直播第169期明道云如何使用明道云.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/intro/主流零代码平台分析报告.md`
  2.    `mingdao/intro/明道云特性清单.md`
  3.    `mingdao/intro/_蒸馏洞察.md`
  4.    `mingdao/live-series/2023/zls-0156-零代码实践第156期利用明道云实现自定义数据打印功能.md`
  5.    `mingdao/live-series/2023/hap-0169-HAP实战直播第169期明道云如何使用明道云.md`

### Q13. 华夏银行 i 助手平台部署了多少个应用

- **Kind:** needle
- **Expected:** `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`
  3.    `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  4.    `mingdao/intro/_蒸馏洞察.md`
  5.    `mingdao/cases/open-day/广汽本田汽车有限公司-明道云在广汽本田的人才培养推广经验.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`
  3.    `mingdao/live-series/2023/zls-0158-零代码实践第158期解决方案分享零代码助力中国地质大学智慧学院建设.md`
  4.    `mingdao/cases/open-day/_蒸馏洞察.md`
  5.    `mingdao/intro/_蒸馏洞察.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/intro/明道云在APaaS细分市场中的领先性详解和实证.md`
  2.    `mingdao/cases/open-day/华夏银行股份有限公司-华夏银行实现全员业技融合的低代码推广经验.md`
  3.    `mingdao/cases/all-hands-on/广州红菱电热设备有限公司-从破釜沉舟到破茧重生-一号位的数字化自我救赎.md`
  4.    `mingdao/intro/_蒸馏洞察.md`
  5.    `mingdao/cases/open-day/_蒸馏洞察.md`

### Q14. MPC2025 武测空间无人机日均飞行架次数量

- **Kind:** needle
- **Expected:** `mingdao/cases/mpc2025/_蒸馏洞察.md`
- **vector** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2.    `mingdao/cases/mpc2025/深圳市武测空间信息有限公-零代码赋能低空经济“圳飞”无人机机场的智能管理平台.md`
  3.    `mingdao/live-series/2024/hap-0183-HAP实战直播第183期零代码+GIS实现测绘数字化助力低空经济快速落.md`
  4.    `mingdao/伙伴企微群/_蒸馏洞察.md`
  5.    `mingdao/cases/mpc2025/西安云开信息技术有限公司-明道云在突发事件现场态势感知的应用.md`
- **bm25** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2.    `mingdao/cases/mpc2025/深圳市武测空间信息有限公-零代码赋能低空经济“圳飞”无人机机场的智能管理平台.md`
  3.    `mingdao/live-series/2024/hap-0183-HAP实战直播第183期零代码+GIS实现测绘数字化助力低空经济快速落.md`
  4.    `mingdao/cases/mpc2023/_蒸馏洞察.md`
  5.    `mingdao/cases/mpc2022/_蒸馏洞察.md`
- **hybrid** (rank: 1):
  1. 👉 `mingdao/cases/mpc2025/_蒸馏洞察.md`
  2.    `mingdao/cases/mpc2025/深圳市武测空间信息有限公-零代码赋能低空经济“圳飞”无人机机场的智能管理平台.md`
  3.    `mingdao/live-series/2024/hap-0183-HAP实战直播第183期零代码+GIS实现测绘数字化助力低空经济快速落.md`
  4.    `mingdao/伙伴企微群/_蒸馏洞察.md`
  5.    `mingdao/cases/mpc2023/_蒸馏洞察.md`

### Q15. Nocoly HAP vs Outsystems builder accessibility differences

- **Kind:** needle
- **Expected:** `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
- **vector** (rank: 1):
  1. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  2.    `nocoly/intro/02_partner-program/Nocoly Partnership Essentials.md`
  3.    `nocoly/intro/01_company-brand/Nocoly Marketing Content.md`
  4.    `mingdao/cases/mpc2024/Catomind-Lim-从本地成功到国际拓展启舵科技与-HAP-的战略合作.md`
  5.    `mingdao/intro/明道云HAP introbook.md`
- **bm25** (rank: 2):
  1.    `nocoly/intro/03_product-sales-enablement/FAQ of Nocoly Sales Activity.md`
  2. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  3.    `nocoly/intro/_蒸馏洞察.md`
  4.    `nocoly/intro/01_company-brand/Nocoly Introbook.md`
  5.    `mingdao/cases/mpc2024/Catomind-Lim-从本地成功到国际拓展启舵科技与-HAP-的战略合作.md`
- **hybrid** (rank: 1):
  1. 👉 `nocoly/intro/03_product-sales-enablement/Nocoly HAP Comparison.md`
  2.    `nocoly/intro/03_product-sales-enablement/FAQ of Nocoly Sales Activity.md`
  3.    `nocoly/intro/01_company-brand/Nocoly Marketing Content.md`
  4.    `nocoly/intro/02_partner-program/Nocoly Partnership Essentials.md`
  5.    `nocoly/intro/_蒸馏洞察.md`

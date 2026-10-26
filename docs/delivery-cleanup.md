# 颐和园三端交付清理记录

## 最终范围

仅保留三个业务端：Web景区数字人服务站、Web管理员端、iOS/Android手机App。保留三端共用的后端、数据库、素材、必要部署及维护/回归工具；未新增业务端。

- `frontend/`：服务站、管理员、登录及404，当前生产构建在 `frontend/dist/`。
- `app/`：唯一原生App源码，10个注册页面；已编译的原生资源在 `app/unpackage/dist/build/app-plus/`。
- `server/base/`：真实账号、服务站、景点与路线、导览、知识库、星云、语音、识景、邮件注册与统计。
- `server/digital_human/`：仍被管理员数字人素材/口型功能调用的可选worker及依赖；默认后端不用安装GPU环境。保留它是为了避免破坏现有三端功能，不是另一个业务端。
- `shared/`、`data/`、`static/`：实际使用的颐和园数据、地图、坐标、知识、图标与图片，保留来源及第三方许可证。
- 保留当前正在使用的账号、颐和园导览及用户历史；公开交付包不带这些私有记录。

## 数据库

本项目数据库为 `zhiyou-zhijing-database`，宿主机25432、命名卷 `zhiyou-zhijing-postgres`。保留16个颐和园景点、3条数据库路线、2个数字人、24份知识文档；景点ID保持不变。动态推荐还会使用已保留的颐和园路线资料，不按数据库预设条数限制展示。

同一事务删除已软删除、无业务引用的“故宫博物院”“长城(八达岭)”两条旧测试景点，以及六张旧商品/直播表：

- `chat_message_info`
- `on_air_room_status_item`
- `sales_doc_and_video_info`
- `stream_room_info`
- `streamer_info`
- `product_info`

未修改其它项目的15432/15433数据库或其容器、数据卷。保留的业务记录和所有有效颐和园内容已核对。新ORM不会重新创建旧商品表。

## 已移出项目的内容

- 旧商品/直播模型、独立FunASR/GPT-SoVITS、训练/Agent和旧向量RAG链；默认后端固定使用现有BM25+TF-IDF，原检索阈值和问答规则保持不变。
- App未使用的favorites/rank页面、重复API包装、旧导航组件、未挂载语音组件、旧深色CSS、旧字体图标和多余图标；当前SVG图标、宋体和字号不变。
- Web重复引导图、未使用Logo/favicon及未使用的devtools依赖。
- 旧三套资源包、灵山原始资料、旧商品图片、旧导入/一次性修复脚本和过时全量GPU部署入口。
- 旧截图、历史H5/开发构建、一次性审计副本、计划和报告、临时数据库/资源导入副本及Python缓存。历史内容均归档到项目外。
- 浏览器回归仍保留10个有效脚本，必要公开fixture迁入App测试目录；只移走3个已失效的旧界面脚本及旧资源比对脚本。

当前运行服务仍占用4个日志文件，保留在忽略的 `work_dirs/` 目录；它们不进入公开交付包。已安装的 `node_modules` 属于本机开发环境，也不进入交付包；包与版本由各端锁文件复现。

## 部署与验证

- 默认数据库端口统一25432，后端统一18000，Compose使用正确的颐和园命名卷。
- 默认CPU后端依赖在外部全新Python3.12环境从零安装通过，`pip check`无冲突。
- Docker后端改为轻量Python镜像，`.env`、密钥、备份、游客数据与缓存不被复制进镜像。
- 增加Web生产Nginx托管，SPA刷新和API代理已用真实Nginx1.28容器验证。手机扫码生产构建必须显式设置 `PUBLIC_SERVER_ORIGIN`，当前领取范围仍为局域网HTTP18000。
- 公开内容包统一为 `resources/summer-palace-content.zip`，ZIP/素材SHA-256校验和导入导出测试通过。旧包不再作为默认导入入口。
- Web：160项测试通过，类型、字号、生产构建通过。
- App：133项单元测试、SDK发布检查、原生资源编译通过；标签切换3个尺寸、领取流程6组语言/尺寸及失败/登录场景检查通过。
- 后端：197项隔离测试、全部模块导入及ORM mapper通过，115条现有接口路径保留；隔离测试禁止连接生产库。
- `python scripts/check_delivery.py --database`：只读验收通过，确认全部景点属于颐和园且旧商品表不存在。

## 交付边界

本次完成代码/数据清理、依赖复现与构建验证，未制作新的正式签名APK或IPA。HBuilder原生资源不等于独立安装包；iPhone声音、最终签名包权限及外部唤起仍需在目标设备验收。此前用户已要求停止iPhone声音修复，本次未擅自继续修改音频方案。

本次未重新进行整套收费云模型答题评测或重装GPU口型环境；保留相应现有实现、题集、阈值和真实配置状态，不将“已配置”伪称为云端调用成功。

## 备份与回溯

完整源码快照和清理前PostgreSQL备份已保存在项目所有者的本机项目外目录。源码ZIP做过CRC校验，数据库dump做过pg_restore目录校验。所有被归档内容和完整逐文件删除记录、测试日志也在本机归档中；公开仓库不包含这些私人备份。

下列是本次移出的源码、旧资源及文档路径（不列数千个历史构建/截图文件）：

- `app/api/index.js`
- `app/common/api.js`
- `app/common/nocturne.css`
- `app/common/planning-underline.js`
- `app/components/TabBarNav.vue`
- `app/components/chat-voice.vue`
- `app/pages/favorites/favorites.vue`
- `app/pages/rank/rank.vue`
- `app/scripts/verify-main-resources.py`
- `app/static/iconfont/icon-custom.css`
- `app/static/iconfont/iconfont.css`
- `app/static/iconfont/iconfont.ttf`
- `app/static/iconfont/iconfont.woff`
- `app/static/iconfont/iconfont.woff2`
- `app/static/tour-orb-pin.svg`
- `app/tests/ai-chat-browser.cjs`
- `app/tests/ai-chat-welcome-browser.cjs`
- `app/tests/route-browser.cjs`
- `configs/api_cfg.yaml`
- `configs/conversation_cfg.yaml`
- `configs/rag_config.yaml`
- `docker/Dockerfile`
- `docs/2026-10-24-三端代码清理.md`
- `docs/2026-10-24-全项目字号整理.md`
- `docs/2026-10-24-测试报告修复说明.md`
- `docs/provincial-pain-point-implementation.md`
- `docs/reviews/2026-10-26-app-ui-improvements.md`
- `docs/reviews/2026-10-26-app-ui-review.md`
- `docs/superpowers/plans/2026-10-26-admin-menu-interactions.md`
- `docs/superpowers/plans/2026-10-26-app-usability-polish.md`
- `docs/superpowers/plans/2026-10-26-project-icon-polish.md`
- `docs/web-experience-upgrade.md`
- `frontend/public/favicon.ico`
- `frontend/public/onboarding/intro-1.png`
- `frontend/public/onboarding/intro-2.png`
- `frontend/public/onboarding/intro-3.png`
- `frontend/src/assets/logo.png`
- `requirements/asr.txt`
- `requirements/avatar_cartoon.txt`
- `requirements/base.txt`
- `requirements/train.txt`
- `requirements/tts.txt`
- `resources/app-lastest-resources.sha256`
- `resources/app-lastest-resources.zip`
- `resources/local-resources.sha256`
- `resources/local-resources.zip`
- `resources/route-cover-generation-plan.json`
- `resources/scenic-images-README.md`
- `resources/scenic-images-manifest.json`
- `resources/scenic-images.sha256`
- `resources/scenic-images.zip`
- `scripts/apply_summer_palace_photos.py`
- `scripts/build_palace_catalog.py`
- `scripts/connect_generated_guides.py`
- `scripts/expand_summer_palace.py`
- `scripts/export_scenic_images.py`
- `scripts/fix_summer_palace_locations.py`
- `scripts/import_generated_route_covers.py`
- `scripts/import_scenic_spots.py`
- `scripts/import_verified_spot_photos.py`
- `scripts/link_existing_route_photos.py`
- `scripts/migrate_musetalk_windows.py`
- `scripts/migrate_route_cities.py`
- `scripts/recover_phone_view_history.py`
- `scripts/restore_local_spot_photos.py`
- `scripts/seed_summer_palace_demo.py`
- `scripts/shorten_summer_palace_visits.py`
- `scripts/verify_app_motion.cjs`
- `scripts/verify_left_hand_gestures.mjs`
- `scripts/verify_upper_body_gestures.mjs`
- `server/asr/asr_server.py`
- `server/asr/asr_worker.py`
- `server/base/models/llm_model.py`
- `server/base/models/product_model.py`
- `server/base/models/streamer_info_model.py`
- `server/base/models/streamer_room_model.py`
- `server/base/modules/accuracy_tester.py`
- `server/base/modules/rag/feature_store.py`
- `server/base/modules/rag/retriever.py`
- `server/base/modules/rag/test_queries.json`
- `server/tts/modules/__init__.py`
- `server/tts/modules/gpt_sovits/AR/__init__.py`
- `server/tts/modules/gpt_sovits/AR/models/__init__.py`
- `server/tts/modules/gpt_sovits/AR/models/t2s_lightning_module.py`
- `server/tts/modules/gpt_sovits/AR/models/t2s_model.py`
- `server/tts/modules/gpt_sovits/AR/models/utils.py`
- `server/tts/modules/gpt_sovits/AR/modules/__init__.py`
- `server/tts/modules/gpt_sovits/AR/modules/activation.py`
- `server/tts/modules/gpt_sovits/AR/modules/embedding.py`
- `server/tts/modules/gpt_sovits/AR/modules/lr_schedulers.py`
- `server/tts/modules/gpt_sovits/AR/modules/optim.py`
- `server/tts/modules/gpt_sovits/AR/modules/patched_mha_with_cache.py`
- `server/tts/modules/gpt_sovits/AR/modules/scaling.py`
- `server/tts/modules/gpt_sovits/AR/modules/transformer.py`
- `server/tts/modules/gpt_sovits/AR/utils/__init__.py`
- `server/tts/modules/gpt_sovits/AR/utils/initialize.py`
- `server/tts/modules/gpt_sovits/AR/utils/io.py`
- `server/tts/modules/gpt_sovits/inference_gpt_sovits.py`
- `server/tts/modules/gpt_sovits/module/__init__.py`
- `server/tts/modules/gpt_sovits/module/attentions.py`
- `server/tts/modules/gpt_sovits/module/cnhubert.py`
- `server/tts/modules/gpt_sovits/module/commons.py`
- `server/tts/modules/gpt_sovits/module/core_vq.py`
- `server/tts/modules/gpt_sovits/module/mel_processing.py`
- `server/tts/modules/gpt_sovits/module/models.py`
- `server/tts/modules/gpt_sovits/module/modules.py`
- `server/tts/modules/gpt_sovits/module/mrte_model.py`
- `server/tts/modules/gpt_sovits/module/quantize.py`
- `server/tts/modules/gpt_sovits/module/transforms.py`
- `server/tts/modules/gpt_sovits/text/__init__.py`
- `server/tts/modules/gpt_sovits/text/chinese.py`
- `server/tts/modules/gpt_sovits/text/cleaner.py`
- `server/tts/modules/gpt_sovits/text/cmudict-fast.rep`
- `server/tts/modules/gpt_sovits/text/cmudict.rep`
- `server/tts/modules/gpt_sovits/text/engdict-hot.rep`
- `server/tts/modules/gpt_sovits/text/engdict_cache.pickle`
- `server/tts/modules/gpt_sovits/text/english.py`
- `server/tts/modules/gpt_sovits/text/namedict_cache.pickle`
- `server/tts/modules/gpt_sovits/text/opencpop-strict.txt`
- `server/tts/modules/gpt_sovits/text/symbols.py`
- `server/tts/modules/gpt_sovits/text/tone_sandhi.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/README.md`
- `server/tts/modules/gpt_sovits/text/zh_normalization/__init__.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/char_convert.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/chronology.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/constants.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/num.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/phonecode.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/quantifier.py`
- `server/tts/modules/gpt_sovits/text/zh_normalization/text_normlization.py`
- `server/tts/modules/gpt_sovits/utils.py`
- `server/tts/modules/sambert_hifigan/tts_sambert_hifigan.py`
- `server/tts/modules/tts_worker.py`
- `server/tts/tools.py`
- `server/tts/tts_server.py`
- `static/iconfont-preview.html`
- `static/product_files/images/1791628955__b22e900eba36423ebc7a04fc172941f9.png`
- `static/product_files/images/1791628958__79ba51c90f384e2f9d6c5dcd0b1cdfdf.png`
- `utils/__init__.py`
- `游览说明/灵山大佛.png`
- `游览说明/灵山胜境.md`
- `游览说明/颐和园.md`

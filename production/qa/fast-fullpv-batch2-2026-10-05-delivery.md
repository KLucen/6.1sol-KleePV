# 可莉 PV 第二批续作交付, 2026-10-05

## 新导出

完整青空侧脸镜头 [911,1008)，保留原97视频帧、36个源cel、53次原曝光、4.042秒与原AAC载荷。均为未授予美术验收的draft，不是完整PV。

- 单版：`output/klee-cyan-911-1008-fast-draft-v1.mp4`，SHA `d6fc2c5829ad263403af221669a2d28890cc52900963bf1f1ffd2cad8c887386`。
- 左原版/右可莉：`output/klee-cyan-911-1008-comparison-fast-draft-v1.mp4`，SHA `7b6a51b6db42306075ffb122d37c4926f886918306853dce06223995a6c1b0a2`。
- 时间轴：`timeline-cyan-911-1008-fast-draft-v1.json`，不因后续全片选稿增加而重写其未用资产记录。
- 两版各17项技术核验通过：精确源PTS、结束曝光、帧数、AAC时戳/配置/载荷及完整解码。报告 `qa/cyan-911-1008-fast-v1-single-verification.json`、`qa/cyan-911-1008-fast-v1-comparison-verification.json`。

## 本批推进

跨日保存的第二批27次内置imagegen补25个缺稿，63个源视频帧；其中两次定向返修用于975发束/981低头幅度，两个v1未选。此次续作再7次：1043/1048/1053/1059/1064/1069六个新缺稿覆盖37帧，以及已映射1017后脑原长发残条的一次整帧修复。累计34次、31个新缺稿、3次定向修复；不能把版本数当作独立动作数。

生图及青空导出时封存草稿映射420/689，缺269；覆盖2504/3658帧（68.452706%）。随后两条真实人物原稿复用核验后，当前映射422/689，缺267；覆盖2515/3658帧（68.753417%），连续可用映射[0,1091)边界原PTS45.458秒，未重新导整个前段。库存538PNG/543job，265稿结构化待修项是缺陷下限。显式未通过305、未记录117、明确美术通过0；未记录不代表判废。所有新增稿及两条别名引用稿accepted=false。

## 实际检查与经验

青空独立来源97帧逐一核对，36canonical ref像素完全一致、注册字形位移唯一最优(0,0)，字幕实际在966切换，位于人物cel965的曝光内部。全97原始合成字芯RGB精确，注册支持区外零像素变化。全13原尺寸字幕页与9页人物图静态查看；两版编码分别全97帧/各13原尺寸页检查，未见本批字幕/图层阻断。原速观看及全片美术验收未完成。

原f933/935 PNG淡蓝发被sky classifier误删，不是生成缺陷；生成/源matte独立处理，修后保留头发。f967/968白色背景星点连接衣边，限定该实际文件/曝光排除125像素，非每帧再生图。此前舞蹈897..910与举臂1225..1284共74帧输入/合成BGR冻结回归不变。root另看修后人物page03及字幕page08；此前全部9人物页/24个native字区的观察不冒充全部原速检查。

原始raw freeze：`qa/fast-fullpv-cyan-layers-2026-10-05/raw-layer-freeze.json`，SHA `a2cd763bb2cbe98f68671c199aff986c095a06684ff7b404f7e9e97beb3b6c0f`。编码freeze同目录 `encoded-layer-freeze.json` SHA `2a0ee4f73b687999394e60f426fab211707c08404cada5e2af1d2546d80ef59d`。编码有损，单版/对照core平均RGB误差4.145/3.940，不能写RGB精确。淡领/绒球上的字填色亮度接近，限定对比边已保留；新旧发型/领型、头位幅度近似等仍待用户首版反馈与原速判断。

六个全身稿当前source/nativeface/actual前后RGB差和轮廓、返回整图及两页连续对照已静态查看。1059头倾方向正确但新增口袋/纽扣/裤边，后两稿不继承该款式；轻微动作幅度、衣长、手指、膝点/靴饰跨稿差异登记，不反复细修。1043前后并非切镜头；不得仅凭family猜姿势。六稿最终分层、字幕、循环原速仍未验收。细录 `qa/standing-missing-2026-10-05/root-static-review.md`。

## 完整 Prompt 与审计

内置工具生成，无API/CLI切换。旧27次完整原始prompt与逐图职责/参考/输出记录保持冻结：`qa/fast-fullpv-batch2-integrity-2026-10-04/batch2-full-27call-promptset.json`，SHA `173f36b5ee4b9fd280b91db09db77c845789ddd5f39a67f58fb9675ae6eef32a`。

新7次完整appendix：`qa/standing-missing-2026-10-05/oct5-full-7call-promptset.json`，SHA `1e6372e9e88024bfac931dc462b0f7f5993e7a823b80236b5ca2b6346e814608`。保留完整提交prompt、按顺序的参考职责、参考尺寸/SHA、原工具文件与项目副本SHA、源曝光和静态限制。f1017实际1671x941、f1064为1672x940，保存后解码实测，未写死缩略尺寸。

独立最终完整性审计 `qa/fast-fullpv-batch2-final-integrity-2026-10-05/final-integrity-audit.json` SHA `a963453a0fe5cdaa9ce01fd76057d82fc1ec940f75b82918d8e17b1e73f224e3` 在420映射快照时全通过；两视频独立ffprobe均97帧，source/timeline/code/所选PNG/字幕供体/两archive/两freeze精确匹配。原始raw freeze是渲染前记录，追加快照明确after_render，不能倒称为渲染前抓取。该历史报告不包括随后两条别名，新增核对另录，不能覆盖旧审计。

选稿与420进度只读快照：`qa/fast-fullpv-batch2-2026-10-05-asset-selections-snapshot.json`、`qa/fast-fullpv-batch2-2026-10-05-progress-snapshot.json`。后续422进度与别名快照保存在`qa/standing-repeat-audit-2026-10-05/`，两组都不覆盖。经验32..36及续作入口已纳入PRODUCTION_LESSONS.md、PRODUCTION_WORKFLOW.md、CONTINUATION_STATE_2026-10-03.md。

## 后续零生图来源审核与中断

后续并行任务`star_finish_oct5`和`standing_repeat_audit_oct5`触发账户用量限制，没有重试、换模型或改用生成通道。root接手本地来源审核，实际查看1048→1080、1053→1085的人物/原尺寸局部AB、RGB差、轮廓及全部1080..1090曝光，核验仅人物原稿重复，零新增调用覆盖11个源帧。背景星星、字幕和曝光仍逐帧取当前原片；1091/1097/1102变姿势未复用，1100/1106保留独立源稿。

扩展审核`qa/standing-repeat-audit-2026-10-05/root-reviewed-alias-extension.json` SHA `b8e7d460efc7ed06bb1c4222fe6a7044ad15902e578feb57eda015c811b1f4c6`，current source_aliases SHA `cd6098a64c8455b08784bb7ec9919f7bfd6bd60550ce7cee83b183fc1c34be20`。核对原source_map/选稿/compose/青空timeline/两个视频/两个封存prompt集/旧完整性报告SHA均未变；11实际原帧与保存source_refs像素及SHA一致。该审核是after_render别名扩展，不授予美术或新别名的字幕图层通过。

## 仍需继续

最早缺稿1091，star_gestures包余28个缺稿；全片还有267个源稿缺口。root再次实际查看f1037原尺寸字幕对照，日文仍碎字；星空1008..1042私有图层尚待尾六帧1037..1042弱笔画及1033帽羽旁背景星点归属完整gate，没有接入compose或交付为完整已验收镜头。已测试证据保留，停止无新依据的阈值循环。下一批从当前库存继续补缺，不重复本批正常稿；已有舞蹈v11、举臂v2、前段V8不回退。受用量限制中断部分仍未完成，全片尚未交付。

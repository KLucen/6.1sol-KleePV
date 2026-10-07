# 可莉PV：2026-10-04补缺批次

本批是两个完整分镜的修正草稿及侧脸补稿，不是完整PV。原速美术与全片连续性验收未完成。

## 当前视频

- 舞蹈单人：[v11](C:/Users/KLucen/Desktop/kl/production/output/klee-dance-812-911-fast-draft-v11.mp4)。原片帧区间[812,911)，99帧、29稿、29次原曝光，视频边界4.125秒。
- 舞蹈左原版/右可莉：[v11对照](C:/Users/KLucen/Desktop/kl/production/output/klee-dance-812-911-comparison-fast-draft-v11.mp4)。
- 举臂单人：[修字幕v2](C:/Users/KLucen/Desktop/kl/production/output/klee-raised-1225-1285-fast-draft-v2.mp4)。原片帧区间[1225,1285)，60帧、13稿、13次原曝光，视频边界2.5秒。
- 举臂左原版/右可莉：[v2对照](C:/Users/KLucen/Desktop/kl/production/output/klee-raised-1225-1285-comparison-fast-draft-v2.mp4)。

四个文件都保持strict_source曝光，原音轨AAC包拷贝；各自17项技术核验通过。解码/时序通过不是人物美术或原速观看通过。

独立[交付完整性核对](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-raised/batch-delivery-integrity-2026-10-04.md)确认四视频实际SHA与各自报告一致，两时间轴、32完整生成记录及快照齐全。本批所有必要导出/检查执行session已结束。

## 本批生图与选稿

内置imagegen共32次调用：24个新增缺稿、4个此前已映射稿的阻断修复、4个未选基线。全部PNG已经复制到项目generated，未用CLI/API绕过，未用定帧、光流或程序画人物补缺。

完整提示词、逐图参考职责、原工具路径、采用版本及SHA见[生成记录](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-batch-2026-10-04-generation-records.json)。记录SHA256：433e3d3cdb4a1046f5e8f4204011a7754b68af478bedd3a0c92ab08056e7f25c。

新增缺稿：舞蹈887/889/903/907/908/909，侧脸938/942/948/954/957/960/963，举臂1225/1229/1234/1241/1248/1256/1264/1267/1274/1278/1282。阻断重绘891/894/897/900。曝光/来源别名没有新增。

## 检查范围

- 舞蹈：99帧原始合成技术检查；变动的两页接触图和900/901原尺寸后帽局部实际查看，其他九页与上一版字节一致。900/901定向清板及原902..910九帧独立matte有12项限定/回归测试，限定区域外和原九帧输出不变。两帧旧动物帽双耳/蓝色接缝已清除，后方可莉帽弧保持遮挡，原星点保留。
- 舞蹈字幕：最终单人v11的99编码帧逐帧顺序解码，13页原尺寸字幕对照已由字层所有者全部查看。812..830安全小字框稳定，897..910新词两行完整，未见新增缺字/碎笔/相位错误。831..896原片/既有星形与字形叠色仍有记录，不声称所有字都清楚。
- 举臂：60帧原始字层和最终60编码帧全部静态查看；单人和对照字幕分别检查，未重现v1丢字/碎笔。根任务及独立检查各有范围记录。奶白领上的1px窄边仅作用真正字形与实际可莉覆盖区。
- 原天空清板、字幕AA与隐藏底板包含重建，不声称原始透明度或隐藏像素完全恢复。未进行不间断原速视觉比较，未给选稿授予最终美术通过。

舞蹈最终[编码字幕人工记录](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-dance-caption-2026-10-04/encoded-v11/STATIC_REVIEW_AND_LIMITS.md)已封存，SHA256 e4069569e60c1ab8b2643294f4719907d4071af1320b4aee1e3858df52e0e3b4。举臂最终[编码字幕与范围记录](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-raised/raised-v2-manual-review.md)保留60帧双版检查证据。

## 全片状态与接续

当前保守cel上限689，389个已有草稿映射，300个缺稿；草稿及确认无人原片复用覆盖2404/3658帧，65.718972%。连续映射[0,965)，原PTS终点40.208秒，但没有重新导出该整个前段。504张生成PNG包括版本，不能当作504个独立动作稿或完片率。

本批选稿与覆盖清单已分别复制为不可复用旧文件名的版本快照：

- [选稿快照](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-batch-2026-10-04-asset-selections-snapshot.json)，SHA256 be0b533d96a1844551d15febe3269c44aff67af1ccd7607ecb557d31795ac857。
- [进度快照](C:/Users/KLucen/Desktop/kl/production/qa/fast-fullpv-batch-2026-10-04-progress-snapshot.json)，SHA256 f2d26d7a95d9b4a4c844623f1102643c2b8f23cea69f87e6510eab7ef2aad2c6。

接续15个侧脸缺稿：965/967/969/973/975/980/981/984/987/992/993/997/998/1002/1003。先读取当前原图/相邻实际二维差值，不重新生成本批已补稿。下一个独立星光手势包还缺46稿。

待复核：侧脸新旧前发/领型切换及位置差，举臂旧稿饰纹/新简领切换与动作幅度、1225上虹膜色、小型帽耳原黑线碎片。后者未确认是完整漏换人物，但不能声称所有原人物像素已移除。可追踪发束和动作跳变仍需原速判断，不能自动降为轻微装饰。

轻微细节登记后继续补缺，阻断项按经验定向处理。完整首版做好后由用户指定返工位置，仅修改相应稿的全部曝光及关联图层；当前不把缺稿占位交付成“完整可莉PV”。

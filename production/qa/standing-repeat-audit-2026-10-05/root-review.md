# 两条真实来源复用审核

root实际查看两组人物AB/RGB差/双色轮廓、全部六处原尺寸关键局部，以及六页未缩放曝光图（1080..1090共11帧）。1048→1080和1053→1085采用identity人物稿别名，不复制星星、背景或字幕，不改source_map及原曝光。所用新可莉稿保持accepted=false；该来源批准不包括最终人物图层、字幕或原速美术验收。

封存扩展审核：`root-reviewed-alias-extension.json`，SHA `b8e7d460efc7ed06bb1c4222fe6a7044ad15902e578feb57eda015c811b1f4c6`。422映射/267缺稿、2515帧覆盖、连续映射至1091，旧420快照仍保留。两个青空视频及其timeline、compose、选稿、源map、旧prompt集和7次appendix均未修改。

另外运行现有make_timeline，写入独立QA文件`timeline-1080-1091-source-alias-check.json`：11源帧、2人物cel、2次曝光，无缺口。该文件仅检查别名解析，不是视频交付；没有重写冻结的青空timeline或扩大星空helper注册范围。

星空私有f1037原尺寸字幕对照再次查看，日文仍缺弱笔画，维持阻断。两个后续并行任务用量限制中断，未重试或换通道。没有新的字形依据时不继续同一套阈值试验；原尺寸图、供体尝试及私有helper保留给下一次定向处理。完整PV尚缺267稿。

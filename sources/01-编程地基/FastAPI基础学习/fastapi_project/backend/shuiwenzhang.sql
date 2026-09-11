-- ----------------------------
-- 数据库：shuiwenzhang（重新执行时删除旧库）
-- ----------------------------
DROP DATABASE IF EXISTS `shuiwenzhang`;
CREATE DATABASE `shuiwenzhang` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `shuiwenzhang`;

-- ----------------------------
-- 表 1：user — 用户表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `user_id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL UNIQUE COMMENT '用户名（邮箱格式）',
  `password` varchar(255) NOT NULL COMMENT '密码（bcrypt 哈希）',
  `nickname` varchar(255) DEFAULT NULL COMMENT '昵称',
  `picture` varchar(255) DEFAULT NULL COMMENT '头像文件名',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `job` varchar(255) DEFAULT NULL COMMENT '职业/身份',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ----------------------------
-- 表 2：article — 文章主表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `article` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `label_name` varchar(100) DEFAULT NULL COMMENT '栏目名称key，如 auto_test、python',
  `article_image` varchar(256) DEFAULT NULL COMMENT '文章头图文件名',
  `title` varchar(256) NOT NULL COMMENT '文章标题',
  `article_content` longtext NOT NULL COMMENT '文章正文（HTML富文本）',
  `article_tag` varchar(64) DEFAULT NULL COMMENT '标签，逗号分隔',
  `user_id` int DEFAULT NULL COMMENT '作者用户ID，外键指向 user.user_id',
  `browse_num` int DEFAULT 0 COMMENT '浏览量',
  `drafted` int DEFAULT NULL COMMENT '草稿标记：0=草稿 1=已发布',
  `article_type` varchar(255) DEFAULT NULL COMMENT '文章类型：原创 / 首发 / 其它',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_label_name` (`label_name`),
  KEY `idx_drafted` (`drafted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章主表';

-- ----------------------------
-- 表 3：comment — 评论/回复表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `comment` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '评论者用户ID',
  `article_id` int NOT NULL COMMENT '被评论的文章ID',
  `ipaddr` varchar(255) NOT NULL COMMENT '评论者IP地址',
  `content` longtext DEFAULT NULL COMMENT '评论内容',
  `reply_id` int DEFAULT 0 COMMENT '回复目标评论ID，0=一级评论',
  `floor_number` int DEFAULT 0 COMMENT '楼层号，按文章维度递增',
  `base_reply_id` int DEFAULT NULL COMMENT '所属一级评论ID，0=一级评论',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_article_id` (`article_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评论/回复表';

-- ----------------------------
-- 表 4：favorite — 收藏表
-- ----------------------------
CREATE TABLE IF NOT EXISTS `favorite` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT '收藏者用户ID',
  `article_id` int NOT NULL COMMENT '被收藏的文章ID',
  `canceled` int DEFAULT 0 COMMENT '0=收藏中 1=已取消收藏（软删除）',
  `create_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_article_id` (`article_id`),
  KEY `idx_canceled` (`canceled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='收藏表';

-- ----------------------------
-- 示例数据：user
-- ----------------------------
INSERT INTO `user` (`user_id`, `username`, `password`, `nickname`, `picture`, `job`, `create_time`) VALUES
(1, 'tester1@shuiwen.com', '$2b$12$i/oxLBHsJofXLxG1kBP07On7HCE5YNKfnUe9mdX0OWuIg9tev5ldW', '水文老王', '1.jpg', '水文监测工程师', '2025-01-10 08:30:00'),
(2, 'tester2@shuiwen.com', '$2b$12$i/oxLBHsJofXLxG1kBP07On7HCE5YNKfnUe9mdX0OWuIg9tev5ldW', '水务小李', '2.jpg', '水质检测员', '2025-02-15 10:00:00'),
(3, 'tester3@shuiwen.com', '$2b$12$i/oxLBHsJofXLxG1kBP07On7HCE5YNKfnUe9mdX0OWuIg9tev5ldW', '水利阿德', '3.jpg', '水利工程师', '2025-03-20 14:20:00');

-- ----------------------------
-- 示例数据：article（已全部转义，可直接执行）
-- ----------------------------
INSERT INTO `article` (`id`, `label_name`, `article_image`, `title`, `article_content`, `article_tag`, `user_id`, `browse_num`, `drafted`, `article_type`, `create_time`) VALUES
(1, 'function_test', 'article_001.jpg', '长江武汉段水质监测与分析', '<p>本文基于 2024 年全年监测数据，对长江武汉段的水质状况进行了系统分析。监测指标包括 pH 值、溶解氧（DO）、化学需氧量（COD）、氨氮（NH₃-N）等。</p><p>结果表明，长江武汉段水质总体稳定，主要污染物浓度呈下降趋势，但局部断面仍存在超标风险。建议加强上游来水管控，增加自动监测站覆盖密度。</p>', '水质监测, 长江, 环境检测', 1, 1250, 1, '原创', '2025-04-01 09:00:00'),
(2, 'function_test', 'article_002.jpg', '如何使用 Python 自动采集水文站数据', '<p>本文介绍如何利用 Python 的 requests 库和定时任务，实现对国家水文信息平台的自动数据采集。</p><pre><code>import requests\nimport schedule\nimport time\n\ndef fetch_data():\n    url = "https://hydata.example.com/api/v1/stations"\n    headers = {"Authorization": "Bearer YOUR_TOKEN"}\n    resp = requests.get(url, headers=headers)\n    print(resp.json())\n\nschedule.every().day.at(\"08:00\").do(fetch_data)\nwhile True:\n    schedule.run_pending()\n    time.sleep(60)</code></pre><p>该方案已在多个省市的水文站点推广使用，采集成功率达 99.5%。</p>', 'Python, 自动化, 水文数据', 2, 890, 1, '首发', '2025-04-08 11:30:00'),
(3, 'function_test', 'article_003.jpg', '水库大坝安全监测技术综述', '<p>水库大坝的安全监测是水利工程管理的核心内容。本文综述了变形监测、渗流监测、应力监测和环境量监测四大类技术的最新进展。</p><p>传统人工监测效率低、频次有限，而自动化监测系统可实现 24 小时实时监控。结合物联网（IoT）技术，传感器数据可同步上传至云平台，异常情况即时告警。</p>', '大坝监测, 安全评估, 物联网', 3, 2100, 1, '原创', '2025-04-15 16:00:00'),
(4, 'function_test', 'article_004.jpg', '南方暴雨洪水预警模型实战', '<p>本文记录了一次完整的暴雨洪水预警建模过程。数据来源为某流域 15 个雨量站 5 年的分钟级降雨数据，结合数字高程模型（DEM）进行汇流计算。</p><p>模型采用新安江模型进行产汇流计算，通过率定验证，相关系数 R² 达到 0.87，预报精度满足甲级标准。</p>', '洪水预报, 新安江模型, 水文学', 1, 680, 1, '原创', '2025-04-20 08:45:00'),
(5, 'auto_test', 'article_005.jpg', '水质传感器数据校验的自动化测试方案', '<p>水质在线监测传感器长期暴露于复杂水体环境中，漂移误差不可避免。本文提出一套基于标准溶液比对的自动化校验方案。</p><p>系统每 24 小时自动切换标准溶液测量管路，计算传感器读数与标准值的偏差，超过阈值时自动发送告警并生成校验报告。该方案将人工校验频次从每周 1 次降低到每月 1 次。</p>', '自动化测试, 水质传感器, 质量控制', 2, 445, 1, '首发', '2025-04-25 13:20:00'),
(6, 'function_test', 'article_006.jpg', '地表水与地下水相互转化研究', '<p>地表水-地下水（SW-GW）转化是水文循环的重要环节。通过示踪试验和数值模拟，本文分析了某平原区河流与地下水之间的补排关系。</p><p>结果表明，枯水期河流主要受地下水补给，补给量约占河道流量的 35%；丰水期则相反，河水向地下水渗透补给。研究成果可为地下水资源合理开发提供依据。</p>', '水文学, 地下水, 数值模拟', 3, 320, 1, '其它', '2025-05-02 10:10:00'),
(7, 'python', 'article_007.jpg', '用 Pandas 处理水利年鉴数据', '<p>本文演示如何使用 Pandas 处理多年的水利年鉴数据，实现数据清洗、统计分析和可视化。</p><pre><code>import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_excel(\'hydrological_yearbook.xlsx\')\ndf[\'year\'] = pd.to_datetime(df[\'date\']).dt.year\nannual_rainfall = df.groupby(\'year\')[\'rainfall\'].sum()\nannual_rainfall.plot(kind=\'bar\', title=\'年均降水量\')\nplt.tight_layout()\nplt.show()</code></pre>', 'Python, Pandas, 数据分析', 1, 1100, 1, '原创', '2025-05-10 09:30:00'),
(8, 'function_test', NULL, 'draft_未发布草稿', '<p>这是草稿状态的文章，还未正式发布。</p>', '草稿', 2, 0, 0, NULL, '2025-05-15 17:00:00');

-- ----------------------------
-- 示例数据：comment
-- ----------------------------
INSERT INTO `comment` (`id`, `user_id`, `article_id`, `ipaddr`, `content`, `reply_id`, `floor_number`, `base_reply_id`, `create_time`) VALUES
(1, 2, 1, '192.168.1.101', '<p>很好的分析！请问数据来源是哪个平台的？</p>', 0, 1, 0, '2025-04-02 10:30:00'),
(2, 1, 1, '192.168.1.102', '<p>数据来自国家水质监测站公开数据，已在文末注明来源。</p>', 1, 1, 1, '2025-04-02 14:15:00'),
(3, 3, 1, '192.168.1.103', '<p>建议增加重金属指标的监测分析，期待后续文章。</p>', 0, 2, 0, '2025-04-03 09:00:00'),
(4, 1, 2, '192.168.1.104', '<p>写得非常实用，已收藏！请问 token 是如何获取的？</p>', 0, 1, 0, '2025-04-09 11:00:00'),
(5, 2, 2, '192.168.1.105', '<p>需要向平台申请 API 权限，审核周期大约 5 个工作日。</p>', 4, 1, 4, '2025-04-09 15:30:00'),
(6, 1, 3, '192.168.1.106', '<p>综述很全面，对我写论文帮助很大。</p>', 0, 1, 0, '2025-04-16 08:30:00'),
(7, 2, 3, '192.168.1.107', '<p>请问渗流监测用的传感器量程是多少？</p>', 0, 2, 0, '2025-04-17 10:00:00'),
(8, 3, 3, '192.168.1.108', '<p>一般量程 0～1m 水头，精度 0.5%FS，具体选型要看大坝类型。</p>', 7, 2, 7, '2025-04-17 11:45:00'),
(9, 2, 4, '192.168.1.109', '<p>R²=0.87 已经很高了，请问用的是哪个工具做的率定？</p>', 0, 1, 0, '2025-04-21 09:00:00'),
(10, 1, 4, '192.168.1.110', '<p>用的是 R 语言的 hydromad 包，非常好用，推荐！</p>', 9, 1, 9, '2025-04-21 14:20:00');

-- ----------------------------
-- 示例数据：favorite
-- ----------------------------
INSERT INTO `favorite` (`id`, `user_id`, `article_id`, `canceled`, `create_time`) VALUES
(1, 2, 1, 0, '2025-04-05 10:00:00'),
(2, 3, 1, 0, '2025-04-06 14:30:00'),
(3, 1, 2, 0, '2025-04-10 09:00:00'),
(4, 3, 2, 0, '2025-04-11 16:00:00'),
(5, 2, 3, 0, '2025-04-18 11:00:00'),
(6, 1, 3, 0, '2025-04-19 08:30:00'),
(7, 3, 4, 0, '2025-04-22 10:00:00'),
(8, 2, 7, 0, '2025-05-12 15:00:00'),
(9, 1, 7, 0, '2025-05-13 09:30:00'),
(10, 2, 1, 1, '2025-04-20 17:00:00');
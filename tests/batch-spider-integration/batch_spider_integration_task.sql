-- ----------------------------
-- Table structure for batch_spider_integration_task
-- ----------------------------
CREATE TABLE `batch_spider_integration_task` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `url` varchar(255) DEFAULT NULL,
  `parser_name` varchar(255) DEFAULT NULL,
  `state` int(11) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Records of batch_spider_integration_task
-- ----------------------------
INSERT INTO `batch_spider_integration_task` VALUES (1, 'https://news.sina.com.cn/', 'SinaNewsParser', 0);
INSERT INTO `batch_spider_integration_task` VALUES (2, 'https://news.qq.com/', 'TencentNewsParser', 0);
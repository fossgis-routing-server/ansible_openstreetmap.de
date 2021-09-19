USE wpblog;

/* Podlove Tabellen löschen: */


DROP TABLE wp_global_podlove_template;
DROP TABLE wp_global_podlove_modules_networks_podcastlist;

DROP TABLE wp_podlove_template;
DROP TABLE wp_podlove_modules_logging_logtable;
DROP TABLE wp_podlove_mediafile;
DROP TABLE wp_podlove_geoareaname;
DROP TABLE wp_podlove_geoarea;
DROP TABLE wp_podlove_filetype;
DROP TABLE wp_podlove_feed;
DROP TABLE wp_podlove_episodeasset;
DROP TABLE wp_podlove_episode;
DROP TABLE wp_podlove_downloadintent;
DROP TABLE wp_podlove_useragent;




/* Blog ID 3 (podcast.openstreetmap.de) löschen */

DELETE FROM wp_blogs WHERE blog_id IN ('3');

DROP TABLE wp_3_terms;
DROP TABLE wp_3_termmeta;
DROP TABLE wp_3_term_taxonomy;
DROP TABLE wp_3_term_relationships;
DROP TABLE wp_3_posts;
DROP TABLE wp_3_postmeta;
DROP TABLE wp_3_podlove_useragent;
DROP TABLE wp_3_podlove_template;
DROP TABLE wp_3_podlove_modules_social_showservice;
DROP TABLE wp_3_podlove_modules_social_service;
DROP TABLE wp_3_podlove_modules_social_contributorservice;
DROP TABLE wp_3_podlove_modules_seasons_season;
DROP TABLE wp_3_podlove_modules_logging_logtable;
DROP TABLE wp_3_podlove_modules_contributors_showcontribution;
DROP TABLE wp_3_podlove_modules_contributors_episodecontribution;
DROP TABLE wp_3_podlove_modules_contributors_defaultcontribution;
DROP TABLE wp_3_podlove_modules_contributors_contributorrole;
DROP TABLE wp_3_podlove_modules_contributors_contributorgroup;
DROP TABLE wp_3_podlove_modules_contributors_contributor;
DROP TABLE wp_3_podlove_modules_analyticsheartbeat_heartbeat;
DROP TABLE wp_3_podlove_mediafile;
DROP TABLE wp_3_podlove_job;
DROP TABLE wp_3_podlove_geoareaname;
DROP TABLE wp_3_podlove_geoarea;
DROP TABLE wp_3_podlove_filetype;
DROP TABLE wp_3_podlove_feed;
DROP TABLE wp_3_podlove_episodeasset;
DROP TABLE wp_3_podlove_episode;
DROP TABLE wp_3_podlove_downloadintentclean;
DROP TABLE wp_3_podlove_downloadintent;
DROP TABLE wp_3_options;
DROP TABLE wp_3_links;
DROP TABLE wp_3_comments;
DROP TABLE wp_3_commentmeta;


/* Unbenutzte Tabellen aus der Migration weeklyosm.eu -> social löschen */

DROP TABLE wp_4_users;
DROP TABLE wp_4_usermeta;




/* WPQuizTabellen löschen: */

DROP TABLE wp_wpvq_quizzes;
DROP TABLE wp_wpvq_questions;
DROP TABLE wp_wpvq_players;
DROP TABLE wp_wpvq_multipliers;
DROP TABLE wp_wpvq_appreciations;
DROP TABLE wp_wpvq_answers;


/* Tabellen von Blog ID 1 (blog.openstreetmap.de) umbennen */

RENAME TABLE `wp_commentmeta` TO `wp_1_commentmeta`;
RENAME TABLE `wp_comments` TO `wp_1_comments`;
RENAME TABLE `wp_links` TO `wp_1_links`;
RENAME TABLE `wp_moppm_user_login_info` TO `wp_1_moppm_user_login_info`;
RENAME TABLE `wp_options` TO `wp_1_options`;
RENAME TABLE `wp_postmeta` TO `wp_1_postmeta`;
RENAME TABLE `wp_posts` TO `wp_1_posts`;
RENAME TABLE `wp_term_relationships` TO `wp_1_term_relationships`;
RENAME TABLE `wp_term_taxonomy` TO `wp_1_term_taxonomy`;
RENAME TABLE `wp_termmeta` TO `wp_1_termmeta`;
RENAME TABLE `wp_terms` TO `wp_1_terms`;
RENAME TABLE `wp_wpvq_answers` TO `wp_1_wpvq_answers`;
RENAME TABLE `wp_wpvq_appreciations` TO `wp_1_wpvq_appreciations`;
RENAME TABLE `wp_wpvq_multipliers` TO `wp_1_wpvq_multipliers`;
RENAME TABLE `wp_wpvq_players` TO `wp_1_wpvq_players`;
RENAME TABLE `wp_wpvq_questions` TO `wp_1_wpvq_questions`;
RENAME TABLE `wp_wpvq_quizzes` TO `wp_1_wpvq_quizzes`;


/* Tabellen von Blog ID 4 (weeklyosm.eu) als default umbennen */

RENAME TABLE `wp_4_ce4wp_contacts` TO `wp_ce4wp_contacts`;
RENAME TABLE `wp_4_commentmeta` TO `wp_commentmeta`;
RENAME TABLE `wp_4_comments` TO `wp_comments`;
RENAME TABLE `wp_4_links` TO `wp_links`;
RENAME TABLE `wp_4_moppm_user_login_info` TO `wp_moppm_user_login_info`;
RENAME TABLE `wp_4_options` TO `wp_options`;
RENAME TABLE `wp_4_postmeta` TO `wp_postmeta`;
RENAME TABLE `wp_4_posts` TO `wp_posts`;
RENAME TABLE `wp_4_term_relationships` TO `wp_term_relationships`;
RENAME TABLE `wp_4_term_taxonomy` TO `wp_term_taxonomy`;
RENAME TABLE `wp_4_termmeta` TO `wp_termmeta`;
RENAME TABLE `wp_4_terms` TO `wp_terms`;
RENAME TABLE `wp_4_wpvq_answers` TO `wp_wpvq_answers`;
RENAME TABLE `wp_4_wpvq_appreciations` TO `wp_wpvq_appreciations`;
RENAME TABLE `wp_4_wpvq_multipliers` TO `wp_wpvq_multipliers`;
RENAME TABLE `wp_4_wpvq_players` TO `wp_wpvq_players`;
RENAME TABLE `wp_4_wpvq_questions` TO `wp_wpvq_questions`;
RENAME TABLE `wp_4_wpvq_quizzes` TO `wp_wpvq_quizzes`;
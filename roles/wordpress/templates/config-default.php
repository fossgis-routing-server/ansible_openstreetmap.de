<?php
define( 'WP_DEBUG', false );

define('DB_NAME', 'wpblog');
define('DB_USER', 'wpblog');
define('DB_PASSWORD', '{{ mysql_password }}');
define('DB_HOST', 'localhost');
define('SECRET_KEY', 'ULvAULnWkgshd8keucq1rpbZbfCzQbSlYb8eLB1L2b');
define('AUTH_KEY', ';7uI%AfCd=ki%BWo/{-rUD#~Yl;/yFPK!C{\%/S$[;8GXU_s3@#IGNJfFSUILI?A<');
define('SECURE_AUTH_KEY', 'lih#!nID,<URG<eV@|c}(YJ~}_O@[JZNw)w8f4p+Hre)K.q89H#bq3u?a[eOH+: ');
define('LOGGED_IN_KEY', ' !1lF2&%S@R4cYE]VRb=q2 ({W$%gG/(!<g<4~uc8wVWH|-t8OT7g)j)X|$P;3_2');
define('NONCE_KEY', '~83KqwB}+J?e.lrQpzF!?C[x2_*#[$?qgM?c;<7ku^Jm@+q,3=POAeywQuX$~6M8');
define('AUTH_SALT', 'G.<$i,baQj|TM/>:Ds5g_2I.nrYm.LQ8Il+.Is|!wyQ=~1s=-m3Hk4te[yJX/rsp');
define('SECURE_AUTH_SALT', '>iKIeouO-`WbvDdV}7>XE1YWK*`M20R*=Dg#XK@SOO^kPtjqr?,DAIL`0U|;hXAR');
define('LOGGED_IN_SALT', '7Txr&USt&-q]b9)|K/f=5<[&NX<x#9z0C-uU<BRAg[+p3dPVd8ZR$q>`RF{@9Jx.');
define('NONCE_SALT', 'eq`%+m%+o7U{eIt-9*u#~MKXfADVH))Lm3vY|o^{8c<,BYi|{Hy|I]$ch#!0KZ$(');



define('ABSPATH', '/var/www/wordpress/');
#define('WPCACHEHOME', ABSPATH.'wp-content/plugins/wp-super-cache/');
#define('WP_CACHE', true);
define('FS_METHOD', 'direct');

define('WPLANG', 'de_DE');
define('DB_CHARSET', 'utf8');

#This will disable the update notification.
#define('WP_CORE_UPDATE', false);


define('MULTISITE', false);
define('SUBDOMAIN_INSTALL', false);
define('DOMAIN_CURRENT_SITE', 'weeklyosm.eu');
# If you change DOMAIN_CURRENT_SITE also change settings in database, especally in tables wp_blogs and wp_settings --Andi
define('PATH_CURRENT_SITE', '/');
define('SITE_ID_CURRENT_SITE', 1);
define('BLOG_ID_CURRENT_SITE', 1);

$table_prefix  = 'wp_';
$server = DB_HOST;
$loginsql = DB_USER;
$passsql = DB_PASSWORD;
$base = DB_NAME;
$upload_path = "/var/lib/wordpress/wp-uploads";
# Upload path changed (old version see above) to make uploading work at blog.openstreetmap.de -- michaelr 2019-04-20
#$upload_path = "/var/lib/wordpress/wp-content/uploads";
$upload_url_path = "https://weeklyosm.eu/wp-uploads";


?>
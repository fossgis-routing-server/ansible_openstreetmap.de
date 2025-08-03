<?php

/**
 * Ephemeris Child Theme functions and definitions
 *
 * A child theme allows you to change small aspects of your site's appearance
 * yet still preserve your theme’s look and functionality.
 * https://developer.wordpress.org/themes/advanced-topics/child-themes/
 *
 * There's no need to include the Ephemeris parent theme's style.css file in here,
 * as Ephemeris will automatically do that for you :-)
 *
 * Since the child theme's functions.php file is included before the parent theme's
 * file, any function within Ephemeris that is wrapped in a function_exists() call,
 * can be overriden by creating that same function within this file. For more details
 * on how to do this, visit the WordPress Developers guide on WordPress.org
 * https://developer.wordpress.org/themes/advanced-topics/child-themes/#using-functions-php
 *
 * Text Domain: ephemeris
 *
 */

/**
 * Removes google fonts from server (added locally again in css)
 *
 */
function ephemeris_fonts_url()
{
  return '';
}

/**
 * disables empty searches, mostly triggered by search engines
 *
 */
add_filter('relevanssi_search_ok', function ($ok, $query) {
  if (empty($query->query_vars['s'])) {
    $ok = false;
  }
  return $ok;
}, 10, 2);

/**
 * Hides and shows the menu button on mobile view based on scroll direction
 */
function hide_mobile_nav_icon()
{
?>
  <script>
    (function() {
      let lastScrollTop = 0;
      const hideAtHeight = 200; // pixel to scroll to hide the menu button
      const mobileNavigation = document.getElementById('mobile-site-navigation');

      document.addEventListener('scroll', () => {
        const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;

        // scrolling down hides the menu button
        if (currentScrollTop > lastScrollTop && currentScrollTop > hideAtHeight) {
          mobileNavigation.style.transform = 'translateY(-100%)';
          mobileNavigation.style.opacity = '0';
          mobileNavigation.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
        }
        // scrolling up shows the manu button again
        else if (currentScrollTop < lastScrollTop) {
          mobileNavigation.style.transform = 'translateY(0)';
          mobileNavigation.style.opacity = '1';
          mobileNavigation.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
        }

        lastScrollTop = currentScrollTop <= 0 ? 0 : currentScrollTop;
      });
    })();
  </script>
<?php
}

add_action('wp_footer', 'hide_mobile_nav_icon', 100);

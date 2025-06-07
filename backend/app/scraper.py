"""
Website scraping module using Browserbase SDK with Playwright for reliable web scraping
"""

import os
import base64
import json
import os
import asyncio
import httpx
import socket
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Tuple, Optional, List
from dotenv import load_dotenv
from urllib.parse import urljoin, urlparse
from contextlib import asynccontextmanager

# For Playwright and Browserbase SDK
from browserbase import Browserbase
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# API keys and credentials
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

class WebsiteScraper:
    def __init__(self):
        """
        Initialize the WebsiteScraper
        """
        self.client = httpx.AsyncClient()
        print(f"WebsiteScraper initialized with Browserbase SDK")
        
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Scrape a website and extract useful design context using Browserbase
        
        Args:
            url: The URL of the website to scrape
            
        Returns:
            Dict containing HTML, CSS, DOM structure, and design elements
        """
        if not url:
            raise ValueError("URL cannot be empty")
            
        # Ensure URL has a scheme
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
            
        try:
            # Validate URL format
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError(f"Invalid URL format: {url}")
                
            print(f"Scraping website: {url}")
            
            # Get page content and screenshot
            html_content, screenshot = await self._get_page_content_and_screenshot(url)
            
            if not html_content:
                raise ValueError("Failed to retrieve HTML content")
                
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract CSS, script tags, and meta tags
            css_content = self._extract_css_content(soup, url)
            js_content = self._extract_js_content(soup, url)
            meta_tags = self._extract_meta_tags(soup)
            
            # Extract key design elements
            design_elements = self._extract_design_elements(soup)
            
            # Extract detailed DOM structure
            dom_analysis = self._analyze_dom_structure(soup)
            
            # Process visual elements (requires screenshot to be analyzed)
            visual_elements = await self._identify_visual_elements(html_content, screenshot, soup)
            
            # Catalog all assets (images, icons, SVGs, videos, etc.)
            asset_catalog = self._catalog_assets(soup, url)
            
            # Compute detailed layout metrics
            layout_metrics = await self._compute_layout_metrics(html_content, soup)
            
            # Build the result object
            result = {
                "url": url,
                "title": soup.title.string if soup.title else "",
                "html": html_content,
                "css": css_content,
                "js": js_content,
                "meta": meta_tags,
                "design": design_elements,
                "dom_analysis": dom_analysis,
                "visual_elements": visual_elements,
                "assets": asset_catalog,
                "layout_metrics": layout_metrics,
                "screenshot": screenshot
            }
            
            print(f"Successfully scraped {url}")
            return result
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            raise Exception(f"Error scraping {url}: {str(e)}")
            return {"error": f"Error scraping {url}: {str(e)}"}
    
    async def _get_page_content_and_screenshot(self, url: str) -> Tuple[str, str]:
        """
        Use Browserbase SDK with Playwright to get the full page content and screenshot
        
        Args:
            url: The URL of the website to scrape
            
        Returns:
            Tuple of (html_content, screenshot_data)
        """
        print(f"Starting scrape job for {url}")
        
        # Check if API key is available
        if not BROWSERBASE_API_KEY:
            raise ValueError("BROWSERBASE_API_KEY is not set in environment variables")
        
        try:
            # Create a Browserbase instance
            bb = Browserbase(api_key=BROWSERBASE_API_KEY)
            print(f"Connected to Browserbase with API key")
            
            # Create a new session with the required project_id parameter
            session = bb.sessions.create(project_id=BROWSERBASE_PROJECT_ID)
            print(f"Created Browserbase session with ID: {session.id}")
            print(f"Session replay available at: https://browserbase.com/sessions/{session.id}")
            
            html_content = ""
            screenshot_data = ""
            
            # Use Playwright to interact with the Browserbase session
            async with async_playwright() as p:
                # Connect to the Browserbase session
                browser = await p.chromium.connect_over_cdp(session.connect_url)
                
                # Get the default context and page
                context = browser.contexts[0]
                page = context.pages[0]
                
                try:
                    # Navigate to the target URL with a timeout
                    print(f"Navigating to {url}...")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    print(f"Successfully loaded {url}")
                    
                    # Wait a bit for any lazy-loaded content
                    await asyncio.sleep(2)
                    
                    # Get the full HTML content
                    html_content = await page.content()
                    print(f"Retrieved HTML content, length: {len(html_content)}")
                    
                    # Take a screenshot - returns binary data
                    screenshot_data = await page.screenshot(full_page=True, type="jpeg", quality=80)
                    print(f"Captured screenshot, size: {len(screenshot_data) if screenshot_data else 0} bytes")
                    
                    # For screenshots, we need to convert binary data to base64 string
                    if isinstance(screenshot_data, bytes):
                        import base64
                        screenshot_data = base64.b64encode(screenshot_data).decode('ascii')
                        print(f"Converted screenshot to base64, length: {len(screenshot_data)}")
                    else:
                        screenshot_data = ""
                    
                except Exception as e:
                    print(f"Error during page navigation or content extraction: {str(e)}")
                    raise
                    
                finally:
                    # Clean up resources
                    await browser.close()
                    print("Browser session closed")
                    
            # Return the HTML and screenshot
            return html_content, screenshot_data
            
        except Exception as e:
            print(f"Error during Browserbase scraping: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise  # No fallback, as requested by the user
    
    def _extract_css_content(self, soup, base_url):
        """
        Extract CSS content from style tags and linked stylesheets
        """
        css_content = []
        
        # Extract inline styles
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                css_content.append({
                    "type": "inline",
                    "content": style_tag.string
                })
        
        # Extract linked stylesheets
        for link_tag in soup.find_all('link', rel='stylesheet'):
            href = link_tag.get('href')
            if href:
                css_content.append({
                    "type": "external",
                    "url": urljoin(base_url, href),
                    "media": link_tag.get('media', 'all')
                })
        
        print(f"Extracted {len(css_content)} CSS sources")
        return css_content
    
    def _extract_js_content(self, soup, base_url):
        """
        Extract JavaScript content from script tags
        """
        js_content = []
        
        # Extract inline scripts
        for script_tag in soup.find_all('script'):
            # Skip if it has a src attribute (external script)
            if script_tag.has_attr('src'):
                js_content.append({
                    "type": "external",
                    "url": urljoin(base_url, script_tag['src'])
                })
            elif script_tag.string:
                js_content.append({
                    "type": "inline",
                    "content": script_tag.string
                })
        
        print(f"Extracted {len(js_content)} JavaScript sources")
        return js_content
    
    def _extract_meta_tags(self, soup):
        """
        Extract meta tags from the HTML
        """
        meta_tags = []
        
        for meta in soup.find_all('meta'):
            meta_dict = {}
            
            for attr in ['name', 'property', 'content', 'charset', 'http-equiv']:
                if meta.has_attr(attr):
                    meta_dict[attr] = meta[attr]
            
            if meta_dict:  # Only append if we found attributes
                meta_tags.append(meta_dict)
        
        print(f"Extracted {len(meta_tags)} meta tags")
        return meta_tags
    
    def _extract_design_elements(self, soup):
        """
        Extract key design elements from the page including fonts, colors, and layout
        """
        import re
        
        design_elements = {
            "headings": {},
            "colors": [],
            "fonts": [],
            "layout": {
                "containers": 0,
                "grid_systems": False,
                "flexbox_usage": False
            }
        }
        
        # Extract headings
        for i in range(1, 7):
            headings = soup.find_all(f'h{i}')
            if headings:
                design_elements["headings"][f"h{i}"] = len(headings)
        
        # Extract fonts from style tags and CSS
        fonts = set()
        
        # Check for font-family in style tags
        for style in soup.find_all('style'):
            if style.string:
                # Extract font-family declarations
                font_matches = re.findall(r'font-family:\s*([^;}]+)[;}]', style.string)
                for match in font_matches:
                    # Split multiple fonts and clean up quotes
                    for font in match.split(','):
                        cleaned_font = font.strip().strip('\'"').strip()
                        if cleaned_font and cleaned_font.lower() not in ['inherit', 'initial']:
                            fonts.add(cleaned_font)
        
        # Check for font-family in inline styles
        for element in soup.find_all(style=True):
            style_attr = element.get('style', '')
            font_matches = re.findall(r'font-family:\s*([^;}]+)[;}]', style_attr)
            for match in font_matches:
                for font in match.split(','):
                    cleaned_font = font.strip().strip('\'"').strip()
                    if cleaned_font and cleaned_font.lower() not in ['inherit', 'initial']:
                        fonts.add(cleaned_font)
        
        # Extract colors from style tags and CSS
        colors = set()
        color_pattern = r'(?:color|background|background-color|border-color):\s*([#][0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|[a-zA-Z]+)[;}]'
        
        # Look for colors in style tags
        for style in soup.find_all('style'):
            if style.string:
                color_matches = re.findall(color_pattern, style.string)
                for color in color_matches:
                    colors.add(color.strip())
        
        # Look for colors in inline styles
        for element in soup.find_all(style=True):
            style_attr = element.get('style', '')
            color_matches = re.findall(color_pattern, style_attr)
            for color in color_matches:
                colors.add(color.strip())
        
        # Check for @font-face declarations
        for style in soup.find_all('style'):
            if style.string:
                font_face_matches = re.findall(r'@font-face\s*{([^}]+)}', style.string)
                for face in font_face_matches:
                    font_family_match = re.search(r'font-family:\s*([^;}]+)[;}]', face)
                    if font_family_match:
                        for font in font_family_match.group(1).split(','):
                            cleaned_font = font.strip().strip('\'"').strip()
                            if cleaned_font:
                                fonts.add(cleaned_font)
        
        # Check for Google Fonts or other font imports
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if 'fonts.googleapis.com' in href:
                # Extract font family from Google Fonts URL
                family_match = re.search(r'family=([^&]+)', href)
                if family_match:
                    families = family_match.group(1).replace('+', ' ').split('|')
                    for family in families:
                        # Remove weight/style specifications
                        base_family = family.split(':')[0]
                        fonts.add(base_family)
        
        # Try to detect if the page is using serif or sans-serif as base
        main_content = soup.find('body')
        text_elements = main_content.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3']) if main_content else []
        
        # Check computed style if available (might require JavaScript)
        is_serif_dominant = False
        serif_indicators = ['serif', 'times', 'georgia', 'cambria', 'palatino', 'garamond']
        
        for element in text_elements[:20]:  # Check first 20 text elements
            if element.get('style'):
                font_family = re.search(r'font-family:\s*([^;]+);', element.get('style', ''))
                if font_family:
                    for serif_font in serif_indicators:
                        if serif_font.lower() in font_family.group(1).lower():
                            is_serif_dominant = True
                            break
        
        # Add common web fonts if none detected (for better cloning)
        if not fonts:
            if is_serif_dominant:
                fonts = {'Times New Roman', 'Georgia', 'Cambria', 'serif', 'Palatino', 'Garamond'}
            else:
                fonts = {'Arial', 'Helvetica', 'Verdana', 'sans-serif', 'Segoe UI', 'Roboto'}
        
        # Simple check for common layout systems
        grid_classes = ['grid', 'row', 'col', 'container']
        flex_classes = ['flex', 'flex-container']
        
        for element in soup.find_all(class_=True):
            classes = element.get('class', [])
            
            # Count containers
            if 'container' in classes:
                design_elements["layout"]["containers"] += 1
            
            # Check for grid systems
            if any(grid_class in ' '.join(classes).lower() for grid_class in grid_classes):
                design_elements["layout"]["grid_systems"] = True
            
            # Check for flexbox
            if any(flex_class in ' '.join(classes).lower() for flex_class in flex_classes):
                design_elements["layout"]["flexbox_usage"] = True
        
        # Update the design elements
        design_elements["fonts"] = list(fonts)
        design_elements["colors"] = list(colors)
        
        print(f"Extracted design elements: {len(design_elements['headings'])} heading types, {len(fonts)} fonts, {len(colors)} colors")
        return design_elements
    
    async def close(self):
        """Close client properly with async context"""
        if hasattr(self, 'client') and not self.client.is_closed:
            await self.client.aclose()
    
    def __del__(self):
        """Attempt to clean up resources when the object is destroyed"""
        if hasattr(self, 'client') and not self.client.is_closed:
            try:
                # Not ideal, but __del__ can't be async
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.client.aclose())
            except:
                pass
                
    def _analyze_dom_structure(self, soup):
        """
        Perform detailed analysis of the DOM structure to identify patterns and hierarchy.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            Dict containing DOM structure analysis results
        """
        print("Analyzing DOM structure...")
        
        # Initialize structure analysis results
        analysis = {
            "element_counts": {},
            "nesting_patterns": [],
            "repeating_structures": [],
            "semantic_structure": {},
            "main_content_area": None,
            "navigation_pattern": None,
            "hierarchy_depth": 0
        }
        
        # Count elements by type
        all_elements = soup.find_all()
        element_counts = {}
        for element in all_elements:
            tag_name = element.name
            if tag_name in element_counts:
                element_counts[tag_name] += 1
            else:
                element_counts[tag_name] = 1
        
        # Sort by frequency to identify important elements
        analysis["element_counts"] = dict(sorted(element_counts.items(), key=lambda x: x[1], reverse=True)[:20])
        
        # Find maximum nesting depth
        def get_depth(element, current_depth=0):
            if not hasattr(element, 'contents'):
                return current_depth
            if not element.contents:
                return current_depth
            return max([get_depth(child, current_depth + 1) for child in element.contents 
                         if hasattr(child, 'contents')] or [current_depth])
        
        analysis["hierarchy_depth"] = get_depth(soup)
        
        # Identify main content area
        content_candidates = soup.find_all(['main', 'article', 'div'], class_=lambda c: c and any(kw in c for kw in ['content', 'main', 'article', 'body']))
        if content_candidates:
            # Choose the one with the most text content
            main_content = max(content_candidates, key=lambda x: len(x.get_text(strip=True)))
            analysis["main_content_area"] = {
                "tag": main_content.name,
                "classes": main_content.get('class', []),
                "id": main_content.get('id', ''),
                "approximate_location": "central" if main_content.name in ['main', 'article'] else "unknown"
            }
        
        # Identify navigation patterns
        nav_elements = soup.find_all(['nav', 'header'])
        if nav_elements:
            nav = nav_elements[0]
            is_horizontal = len(nav.find_all('li', recursive=True)) > len(nav.find_all('ul', recursive=True)) * 3
            analysis["navigation_pattern"] = {
                "type": "horizontal" if is_horizontal else "vertical",
                "item_count": len(nav.find_all('li')),
                "has_dropdown": len(nav.select('ul ul')) > 0,
                "location": "header" if nav.name == "header" or nav.parent.name == "header" else "standalone"
            }
        
        # Identify repeating structures
        repeating_candidates = []
        
        # Look for lists of similar items
        for list_element in soup.find_all(['ul', 'ol', 'div']):
            children = list(list_element.find_all(recursive=False))
            if len(children) >= 3 and all(child.name == children[0].name for child in children):
                # We found a potential repeating structure
                repeating_candidates.append({
                    "parent": list_element.name,
                    "pattern": children[0].name,
                    "count": len(children),
                    "classes": list_element.get('class', []),
                    "likely_content_type": "navigation" if list_element.name in ['ul', 'ol'] and any(a.name == 'a' for a in list_element.find_all('a', recursive=False)) else "content"
                })
        
        # Sort by count to find the most significant repeating patterns
        analysis["repeating_structures"] = sorted(repeating_candidates, key=lambda x: x["count"], reverse=True)[:5]
        
        # Analyze semantic structure
        semantic_tags = ['header', 'nav', 'main', 'article', 'section', 'aside', 'footer']
        semantic_structure = {}
        for tag in semantic_tags:
            elements = soup.find_all(tag)
            if elements:
                semantic_structure[tag] = len(elements)
        analysis["semantic_structure"] = semantic_structure
        
        print(f"DOM analysis complete: found {len(analysis['element_counts'])} unique elements, max depth: {analysis['hierarchy_depth']}")
        return analysis
        
    async def _identify_visual_elements(self, html_content, screenshot_base64, soup):
        """
        Identify visual UI components from the screenshot and map them to DOM elements.
        
        This method analyzes visual components like buttons, cards, images, sliders, etc.
        and connects them with their corresponding DOM elements.
        
        Args:
            html_content: The full HTML content
            screenshot_base64: Base64 encoded screenshot
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            Dict containing identified visual elements
        """
        print("Identifying visual UI elements...")
        
        # Initialize visual elements analysis
        visual_elements = {
            "ui_components": [],
            "color_regions": [],
            "content_sections": [],
            "visual_hierarchy": {},
            "interactive_elements": []
        }
        
        # Identify common UI components based on class names and attributes
        # This approach doesn't rely on the screenshot for analysis, but uses DOM heuristics
        
        # Buttons detection
        buttons = []
        for button in soup.find_all(['button', 'a', 'input']):
            if button.name == 'button' or (button.name == 'input' and button.get('type') in ['button', 'submit', 'reset']) or \
               (button.name == 'a' and button.get('class') and any(cls in ['btn', 'button'] for cls in button.get('class'))):
                style = {}
                if button.get('style'):
                    # Basic style parsing (simplified)
                    style_text = button.get('style')
                    for prop in style_text.split(';'):
                        if ':' in prop:
                            key, value = prop.split(':', 1)
                            style[key.strip()] = value.strip()
                
                buttons.append({
                    "type": "button",
                    "text": button.get_text(strip=True),
                    "classes": button.get('class', []),
                    "id": button.get('id', ''),
                    "styles": style,
                    "is_primary": bool(button.get('class') and any('primary' in cls for cls in button.get('class'))),
                    "element_path": self._get_element_path(button)
                })
        
        # Form elements
        forms = []
        for form in soup.find_all('form'):
            inputs = form.find_all(['input', 'select', 'textarea'])
            forms.append({
                "type": "form",
                "input_count": len(inputs),
                "has_submit": bool(form.find('input', {'type': 'submit'}) or form.find('button')),
                "classes": form.get('class', []),
                "id": form.get('id', ''),
                "element_path": self._get_element_path(form)
            })
            
        # Cards/Panels
        cards = []
        card_candidates = soup.find_all(['div', 'section', 'article'], class_=lambda c: c and any(card_term in c for card_term in ['card', 'panel', 'box', 'tile']))
        for card in card_candidates:
            cards.append({
                "type": "card",
                "has_image": bool(card.find('img')),
                "has_header": bool(card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header'])),
                "has_footer": bool(card.find('footer')),
                "classes": card.get('class', []),
                "id": card.get('id', ''),
                "element_path": self._get_element_path(card)
            })
            
        # Navigation bars
        navbars = []
        for nav in soup.find_all(['nav', 'div', 'header'], class_=lambda c: c and any(nav_term in c for nav_term in ['nav', 'menu', 'navigation'])):
            navbars.append({
                "type": "navbar",
                "item_count": len(nav.find_all('a')),
                "orientation": "horizontal" if nav.name == 'header' or (nav.get('class') and any('header' in cls for cls in nav.get('class'))) else "vertical",
                "classes": nav.get('class', []),
                "id": nav.get('id', ''),
                "element_path": self._get_element_path(nav)
            })
            
        # Identify content sections by looking for headers with content
        content_sections = []
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            # Look for the next sibling elements that might form a content section
            siblings = []
            current = heading.next_sibling
            while current and current.name not in ['h1', 'h2', 'h3']:
                if current.name in ['p', 'ul', 'ol', 'div', 'section']:
                    siblings.append(current)
                current = current.next_sibling
                
            if siblings:
                content_sections.append({
                    "type": "content_section",
                    "heading": heading.get_text(strip=True),
                    "heading_level": int(heading.name[1]),
                    "content_elements": len(siblings),
                    "approximate_length": sum(len(s.get_text(strip=True)) for s in siblings if hasattr(s, 'get_text')),
                    "element_path": self._get_element_path(heading)
                })
        
        # Add all components to the visual elements dict
        visual_elements["ui_components"] = buttons + forms + cards + navbars
        visual_elements["content_sections"] = content_sections
        
        # Interactive elements (anything that has click handlers or href)
        interactive_elements = []
        for element in soup.find_all(['a', 'button', 'input', 'select', 'textarea', 'form']):
            if element.name in ['a', 'button'] or (element.name == 'input' and element.get('type') in ['submit', 'button', 'reset', 'checkbox', 'radio']):
                interactive_elements.append({
                    "type": element.name,
                    "text": element.get_text(strip=True) if element.name != 'input' else element.get('value', ''),
                    "classes": element.get('class', []),
                    "id": element.get('id', ''),
                    "element_path": self._get_element_path(element),
                    "interaction_type": "click"
                })
        
        visual_elements["interactive_elements"] = interactive_elements
        
        print(f"Visual element identification complete: found {len(visual_elements['ui_components'])} UI components, {len(visual_elements['content_sections'])} content sections")
        return visual_elements
    
    def _get_element_path(self, element):
        """Generate a simplified CSS selector path to the element"""
        path = []
        for parent in element.parents:
            if parent.name == 'html':
                break
            
            selector = parent.name
            if parent.get('id'):
                selector += f"#{parent.get('id')}"
            elif parent.get('class'):
                selector += f".{'.'.join(parent.get('class'))}"
            
            path.append(selector)
        
        # Element itself
        selector = element.name
        if element.get('id'):
            selector += f"#{element.get('id')}"
        elif element.get('class'):
            selector += f".{'.'.join(element.get('class'))}"
            
        path.append(selector)
        path.reverse()
        return ' > '.join(path)
        
    def _catalog_assets(self, soup, base_url):
        """
        Create a comprehensive inventory of all assets on the webpage.
        
        This catalogs images, icons, SVGs, videos, audio files, and other media
        with detailed metadata for each asset.
        
        Args:
            soup: BeautifulSoup object of the parsed HTML
            base_url: The base URL of the website
            
        Returns:
            Dict containing categorized assets
        """
        print("Cataloging webpage assets...")
        
        # Initialize the asset catalog
        asset_catalog = {
            "images": [],
            "icons": [],
            "svgs": [],
            "videos": [],
            "audio": [],
            "fonts": [],
            "other_media": [],
            "summary": {}
        }
        
        # Process all image tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # Resolve relative URLs
                full_url = urljoin(base_url, src)
                
                # Determine if it's likely an icon based on size attributes or class
                is_icon = False
                width = img.get('width')
                height = img.get('height')
                
                if width and height:
                    try:
                        w, h = int(width), int(height)
                        is_icon = w <= 64 and h <= 64
                    except ValueError:
                        pass
                
                if not is_icon and img.get('class'):
                    is_icon = any(icon_term in cls for cls in img.get('class') for icon_term in ['icon', 'logo', 'avatar', 'symbol'])
                
                # Extract image information
                img_info = {
                    "url": full_url,
                    "alt_text": img.get('alt', ''),
                    "width": width,
                    "height": height,
                    "loading": img.get('loading', 'eager'),  # lazy or eager loading
                    "classes": img.get('class', []),
                    "element_path": self._get_element_path(img),
                    "estimated_size_category": self._estimate_size_category(width, height)
                }
                
                # Add to appropriate category
                if is_icon:
                    asset_catalog["icons"].append(img_info)
                else:
                    asset_catalog["images"].append(img_info)
        
        # Process inline SVGs
        for svg in soup.find_all('svg'):
            # Extract the SVG content
            svg_code = str(svg)
            
            # Try to determine purpose
            purpose = "unknown"
            if svg.get('class'):
                if any(icon_term in cls for cls in svg.get('class') for icon_term in ['icon', 'logo', 'symbol']):
                    purpose = "icon"
                elif any(term in cls for cls in svg.get('class') for term in ['illustration', 'diagram', 'chart']):
                    purpose = "illustration"
            
            # Get dimensions if available
            width = svg.get('width')
            height = svg.get('height')
            viewBox = svg.get('viewBox')
            
            asset_catalog["svgs"].append({
                "inline": True,
                "code_length": len(svg_code),
                "purpose": purpose,
                "width": width,
                "height": height,
                "viewBox": viewBox,
                "classes": svg.get('class', []),
                "element_path": self._get_element_path(svg)
            })
        
        # Process video elements
        for video in soup.find_all(['video', 'source']):
            src = video.get('src')
            if src:
                full_url = urljoin(base_url, src)
                
                asset_catalog["videos"].append({
                    "url": full_url,
                    "type": video.get('type', ''),
                    "controls": video.has_attr('controls'),
                    "autoplay": video.has_attr('autoplay'),
                    "muted": video.has_attr('muted'),
                    "loop": video.has_attr('loop'),
                    "element_path": self._get_element_path(video)
                })
        
        # Process audio elements
        for audio in soup.find_all(['audio', 'source']):
            if audio.name == 'source' and audio.parent.name != 'audio':
                continue  # Skip video sources
                
            src = audio.get('src')
            if src:
                full_url = urljoin(base_url, src)
                
                asset_catalog["audio"].append({
                    "url": full_url,
                    "type": audio.get('type', ''),
                    "controls": audio.has_attr('controls') if audio.name == 'audio' else audio.parent.has_attr('controls'),
                    "autoplay": audio.has_attr('autoplay') if audio.name == 'audio' else audio.parent.has_attr('autoplay'),
                    "element_path": self._get_element_path(audio)
                })
        
        # Add fonts from @font-face rules and link tags
        font_files = []
        for style in soup.find_all('style'):
            if style.string:
                css_text = style.string
                # Look for @font-face rules
                import re
                font_face_rules = re.findall(r'@font-face\s*{([^}]*)}', css_text)
                for rule in font_face_rules:
                    # Extract font URLs
                    font_urls = re.findall(r'url\([\'\"](.+?)[\'\"]\)', rule)
                    for font_url in font_urls:
                        full_url = urljoin(base_url, font_url)
                        font_files.append({
                            "url": full_url,
                            "source": "font-face",
                            "format": font_url.split('.')[-1] if '.' in font_url else "unknown"
                        })
        
        # Google Fonts
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href', '')
            if 'fonts.googleapis.com' in href:
                font_files.append({
                    "url": href,
                    "source": "google-fonts",
                    "format": "css"
                })
            
        asset_catalog["fonts"] = font_files
        
        # Look for other media files in links and other elements
        media_extensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar']
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and any(href.lower().endswith('.' + ext) for ext in media_extensions):
                full_url = urljoin(base_url, href)
                asset_catalog["other_media"].append({
                    "url": full_url,
                    "type": href.split('.')[-1].lower(),
                    "text": link.get_text(strip=True),
                    "element_path": self._get_element_path(link)
                })
        
        # Create summary of assets
        asset_catalog["summary"] = {
            "total_images": len(asset_catalog["images"]),
            "total_icons": len(asset_catalog["icons"]),
            "total_svgs": len(asset_catalog["svgs"]),
            "total_videos": len(asset_catalog["videos"]),
            "total_audio": len(asset_catalog["audio"]),
            "total_fonts": len(asset_catalog["fonts"]),
            "total_other_media": len(asset_catalog["other_media"]),
            "total_all": len(asset_catalog["images"]) + len(asset_catalog["icons"]) + len(asset_catalog["svgs"]) + 
                      len(asset_catalog["videos"]) + len(asset_catalog["audio"]) + len(asset_catalog["fonts"]) + 
                      len(asset_catalog["other_media"])
        }
        
        print(f"Asset cataloging complete: {asset_catalog['summary']['total_all']} total assets found")
        return asset_catalog
    
    def _estimate_size_category(self, width, height):
        """Estimate size category of an image based on dimensions"""
        try:
            w = int(width) if width else 0
            h = int(height) if height else 0
            
            area = w * h
            
            if area == 0:
                return "unknown"
            elif area <= 1024:  # 32x32
                return "icon"
            elif area <= 40000:  # ~200x200
                return "thumbnail"
            elif area <= 250000:  # ~500x500
                return "medium"
            elif area <= 1000000:  # ~1000x1000
                return "large"
            else:
                return "extra_large"
        except (ValueError, TypeError):
            return "unknown"
            
    async def _compute_layout_metrics(self, html_content, soup):
        """
        Compute detailed layout metrics including spacing patterns, margins, alignments and grid structures.
        
        This method analyzes the page to identify layout patterns and calculates numerical metrics
        for precise responsive design matching.
        
        Args:
            html_content: The full HTML content
            soup: BeautifulSoup object of the parsed HTML
            
        Returns:
            Dict containing computed layout metrics
        """
        print("Computing layout metrics...")
        
        # Initialize layout metrics
        layout_metrics = {
            "spacing_patterns": [],
            "margins": {},
            "alignments": {},
            "grid_metrics": {},
            "common_dimensions": {},
            "container_analysis": {},
            "breakpoints": [],
            "responsive_patterns": {}
        }
        
        try:
            # Analyze spacing patterns using CSS analysis
            # First look for common spacing units in CSS
            spacing_units = {'px': [], 'rem': [], 'em': [], '%': [], 'vh': [], 'vw': []}
            
            # Extract spacing from style tags
            for style in soup.find_all('style'):
                if style.string:
                    css_text = style.string
                    # Look for margin and padding patterns
                    import re
                    # Extract all spacing values with units
                    spacing_matches = re.findall(r'(margin|padding)(-[a-z]+)?\s*:\s*([\d.]+)([a-z%]+)', css_text)
                    for match in spacing_matches:
                        property_name, direction, value, unit = match
                        if unit in spacing_units:
                            try:
                                spacing_units[unit].append(float(value))
                            except ValueError:
                                pass
            
            # Find most common spacing values for each unit
            from collections import Counter
            for unit, values in spacing_units.items():
                if values:
                    counter = Counter(values)
                    most_common = counter.most_common(5)  # Top 5 most common values
                    layout_metrics["spacing_patterns"].append({
                        "unit": unit,
                        "common_values": [value for value, count in most_common],
                        "frequency": {str(value): count for value, count in most_common}
                    })
            
            # Analyze container widths
            container_widths = []
            max_width_elements = []
            
            # Extract max-width values from style tags
            for style in soup.find_all('style'):
                if style.string:
                    css_text = style.string
                    max_width_matches = re.findall(r'max-width\s*:\s*([\d.]+)([a-z%]+)', css_text)
                    for value, unit in max_width_matches:
                        try:
                            if unit == 'px':
                                container_widths.append(float(value))
                        except ValueError:
                            pass
                            
            # Look for common container class patterns
            container_classes = ['container', 'wrapper', 'content', 'main', 'page']
            for cls in container_classes:
                containers = soup.find_all(class_=lambda c: c and cls in c)
                if containers:
                    layout_metrics["container_analysis"][cls] = len(containers)
            
            # Analyze grid system
            grid_system = {
                "type": "unknown",
                "columns": 0,
                "gutter": "unknown"
            }
            
            # Check for Bootstrap-style grid
            bootstrap_cols = soup.find_all(class_=lambda c: c and re.search(r'col(-[a-z]+)?-\d+', c if c else ""))
            if bootstrap_cols:
                grid_system["type"] = "bootstrap"
                grid_system["columns"] = 12  # Bootstrap uses 12-column grid
            
            # Check for CSS Grid
            grid_containers = soup.find_all(class_=lambda c: c and 'grid' in (c if c else []))
            if grid_containers:
                grid_system["type"] = "css-grid"
            
            # Check for flexbox usage
            flex_containers = soup.find_all(class_=lambda c: c and ('flex' in (c if c else []) or 'display-flex' in (c if c else [])))
            if flex_containers and not grid_containers:
                grid_system["type"] = "flexbox"
            
            layout_metrics["grid_metrics"] = grid_system
            
            # Analyze common alignments
            alignment_classes = {
                "text-center": "center",
                "text-left": "left",
                "text-right": "right",
                "align-items-center": "vertical-center",
                "justify-content-center": "horizontal-center"
            }
            
            alignments = {}
            for class_name, alignment in alignment_classes.items():
                elements = soup.find_all(class_=lambda c: c and class_name in (c if c else []))
                if elements:
                    alignments[alignment] = len(elements)
            
            layout_metrics["alignments"] = alignments
            
            # Estimate common margins
            if spacing_units['px']:
                # Find the most common margin/padding values in pixels
                common_margins = Counter(spacing_units['px']).most_common(3)
                layout_metrics["margins"] = {
                    "common_values_px": [value for value, count in common_margins],
                    "most_frequent": common_margins[0][0] if common_margins else 0
                }
            
            # Analyze media queries for responsive breakpoints
            media_queries = []
            for style in soup.find_all('style'):
                if style.string:
                    css_text = style.string
                    media_query_matches = re.findall(r'@media[^{]+\{([^}]+)\}', css_text)
                    for media_query in media_query_matches:
                        width_match = re.search(r'(max|min)-width\s*:\s*([\d.]+)([a-z]+)', media_query)
                        if width_match:
                            condition, value, unit = width_match.groups()
                            try:
                                breakpoint_value = float(value)
                                media_queries.append({
                                    "condition": condition,
                                    "value": breakpoint_value,
                                    "unit": unit
                                })
                            except ValueError:
                                pass
            
            # Extract common breakpoints
            if media_queries:
                breakpoints = []
                for query in media_queries:
                    if query["unit"] == 'px':
                        breakpoints.append(query["value"])
                        
                # Group similar breakpoints (within 20px)
                breakpoints.sort()
                grouped_breakpoints = []
                current_group = [breakpoints[0]] if breakpoints else []
                
                for i in range(1, len(breakpoints)):
                    if breakpoints[i] - current_group[-1] <= 20:  # Within 20px range
                        current_group.append(breakpoints[i])
                    else:
                        grouped_breakpoints.append(sum(current_group) / len(current_group))  # Average value
                        current_group = [breakpoints[i]]
                
                if current_group:
                    grouped_breakpoints.append(sum(current_group) / len(current_group))
                
                layout_metrics["breakpoints"] = grouped_breakpoints
                
                # Identify common responsive patterns
                if len(grouped_breakpoints) >= 3:
                    layout_metrics["responsive_patterns"] = {
                        "type": "multi-breakpoint",
                        "is_mobile_first": any(query["condition"] == "min" for query in media_queries),
                        "breakpoint_count": len(grouped_breakpoints)
                    }
                elif len(grouped_breakpoints) > 0:
                    layout_metrics["responsive_patterns"] = {
                        "type": "simple",
                        "is_mobile_first": any(query["condition"] == "min" for query in media_queries),
                        "breakpoint_count": len(grouped_breakpoints)
                    }
            
            print(f"Layout metrics computed: {len(layout_metrics['spacing_patterns'])} spacing patterns, {len(layout_metrics.get('breakpoints', []))} breakpoints identified")
            
        except Exception as e:
            print(f"Error computing layout metrics: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        return layout_metrics

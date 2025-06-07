"""
LLM integration module using Google's Gemini 1.5 Pro for website cloning
"""

import os
import json
from typing import Dict, Any, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Reset any previous client configuration
genai._client = None

# Get API key from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure with API key only - NO service account
print("Configuring Gemini API with API key authentication ONLY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    print("Successfully configured Gemini with API key")
else:
    print("ERROR: No GOOGLE_API_KEY found in environment variables")


class WebsiteCloner:
    """
    Class for cloning websites using Google's Gemini 1.5 Pro API
    """
    
    def __init__(self):
        try:
            # Get the service account credentials (already globally set above)
            print("Initializing Gemini 1.5 Pro model (using global authentication)")
            
            # Create model instance without specifying any credentials (uses global config)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro",  # Using Gemini 1.5 Pro model
                generation_config={
                    "temperature": 0.05,  # Very low temperature for maximum consistency
                    "top_p": 0.99,
                    "top_k": 40,
                    "max_output_tokens": 100000,  # Reduced from 1M to 100K tokens for faster response
                }
                # No safety_settings to avoid any potential conflicts
            )
            
            print("Successfully initialized Gemini model")
        except Exception as e:
            raise ValueError(f"ERROR: Failed to initialize Gemini model: {str(e)}. Check authentication.")
    
    async def clone_website(self, scrape_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clone a website using Gemini 1.5 Pro based on scraped data
        
        Args:
            scrape_data: Dictionary containing scraped website information
            
        Returns:
            Dictionary containing the cloned HTML and metadata
        """
        try:
            # Extract relevant information from scrape_data
            url = scrape_data.get("url", "")
            print(f"Starting to clone website: {url}")
            
            # Create a detailed prompt from scraped data
            prompt = self._create_prompt(scrape_data)
            
            # Call the model asynchronously
            try:
                print("Sending request to Gemini API...")
                # Generate content with the model - using async with maximum output tokens
                # Set a reasonable timeout for the API call
                import asyncio
                try:
                    # Use a timeout to prevent excessively long waits
                    response = await asyncio.wait_for(
                        self.model.generate_content_async(
                            prompt,
                            generation_config={
                                "max_output_tokens": 100000,  # Reduced for faster response
                                "temperature": 0.1,  # Slightly higher temperature for faster generation
                                "top_p": 0.95,
                                "top_k": 40
                            }
                        ),
                        timeout=60.0  # 60 second timeout
                    )
                except asyncio.TimeoutError:
                    print("Gemini API call timed out after 60 seconds")
                    raise ValueError("API call timed out. The request may be too complex or the model may be overloaded.")
                
                print("Successfully received response from Gemini")
                # Extract just the HTML part
                cloned_html = self._extract_html_from_response(response.text)
                
                # Return the cloned HTML along with metadata
                return {
                    "url": url,
                    "cloned_html": cloned_html,
                    "metadata": {
                        "original_url": url,
                        "cloning_method": "gemini-2.5-pro",
                        "original_structure": scrape_data.get("structure", {})
                    }
                }
            except Exception as api_error:
                error_message = str(api_error)
                print(f"Raw API error: {error_message}")
                
                # Check for quota exceeded errors
                if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
                    error_details = "Quota exceeded or rate limit reached. Please try again later or upgrade your API plan."
                # Check for authentication/permission issues
                elif "403" in error_message or "authentication" in error_message.lower() or "permission" in error_message.lower() or "denied" in error_message.lower():
                    error_details = "Authentication error. Please check your API key or service account credentials."
                # Check for mutual exclusivity errors
                elif "mutually exclusive" in error_message.lower():
                    error_details = "Authentication configuration error: client_options.api_key and credentials are mutually exclusive"
                else:
                    error_details = error_message
                    
                print(f"API error: {error_details}")
                return {"error": f"Failed to generate content: {error_details}"}
                
        except Exception as e:
            print(f"Error in clone_website: {str(e)}")
            return {"error": str(e)}
    
    def _create_prompt(self, scrape_data: Dict[str, Any]) -> str:
        """
        Create a focused, efficient prompt for Gemini 1.5 Pro to clone the website
        """
        # Trim excessive data to optimize prompt size
        self._optimize_scrape_data(scrape_data)
        # Extract relevant information from scrape_data
        url = scrape_data.get("url", "")
        original_html = scrape_data.get("html", "")
        css_data = scrape_data.get("css", [])
        colors = scrape_data.get("colors", [])
        fonts = scrape_data.get("fonts", [])
        structure = scrape_data.get("structure", {})
        
        # Since we have unlimited API access, use the full HTML without truncation
        # This ensures we capture ALL content from the original site
        html_snippet = original_html  # No truncation
        
        # Extract all CSS (inline and external)
        inline_css = ""
        external_css = ""
        for css_item in css_data:
            if css_item.get("type") == "inline" and "content" in css_item:
                inline_css += css_item["content"] + "\n\n"
            elif css_item.get("type") == "external" and "content" in css_item:
                external_css += f"/* From {css_item.get('url', 'external')} */\n{css_item['content']}\n\n"
        
        # Combine CSS with priority to inline
        combined_css = inline_css + "\n" + external_css
        
        # Extract any meta tags for viewport settings
        import re
        meta_tags = ""
        viewport_match = re.search(r'<meta[^>]*?viewport[^>]*?>', original_html)
        if viewport_match:
            meta_tags = viewport_match.group(0)
        
        # Extract DOM structure more precisely
        dom_structure = ""  
        try:
            # Try to find body structure
            body_match = re.search(r'<body[^>]*?>(.*?)</body>', original_html, re.DOTALL)
            if body_match:
                from bs4 import BeautifulSoup
                # Use full body content without truncation
                soup = BeautifulSoup(body_match.group(1), 'html.parser')
                # Get structure with class names for top-level elements
                dom_structure = "\n".join([f"{tag.name}.{tag.get('class', [''])[0] if tag.get('class') else ''}" 
                                     for tag in soup.find_all(recursive=False)])
        except Exception:
            dom_structure = ""  # Fallback if extraction fails
        
        # Prepare structure information including specific HTML aspects
        structure_info = json.dumps(structure, indent=2)
        
        # Extract ALL class names for complete styling fidelity
        class_matches = re.findall(r'class=["\']([^"\'>]+)["\']', original_html)
        important_classes = list(set([cls.strip() for match in class_matches for cls in match.split()]))
        
        # Extract ALL ID names
        id_matches = re.findall(r'id=["\']([^"\'>]+)["\']', original_html)
        important_ids = list(set(id_matches))
        
        # Extract ALL image URLs for complete visual fidelity
        img_matches = re.findall(r'<img[^>]*?src=["\']([^"\'>]+)["\']', original_html)
        important_imgs = list(set(img_matches))
        
        # Highly enhanced prompt with extremely detailed instructions for visual fidelity
        prompt = f"""
        You are an expert website cloning AI that specializes in PIXEL-PERFECT recreation of websites using just HTML and CSS. Your goal is to create a clone that is INDISTINGUISHABLE from the original website in appearance AND CONTAINS ALL THE SAME TEXTUAL CONTENT.
        
        WEBSITE TO CLONE: {url}
        
        ## DESIGN SYSTEM ANALYSIS

        ### COLOR SYSTEM
        PRIMARY COLORS: {', '.join(colors[:10] if colors else ['#000000', '#ffffff'])}
        SECONDARY COLORS: {', '.join(colors[10:30] if len(colors) > 10 else ['#cccccc', '#f0f0f0'])}
        ACCENT COLORS: {', '.join(colors[30:50] if len(colors) > 30 else ['#3366cc', '#ff9900'])}
        
        ### TYPOGRAPHY SYSTEM (EXTREMELY IMPORTANT - MATCH EXACTLY)
        FONTS: {', '.join(fonts if fonts else ['Arial', 'sans-serif'])}
        
        TYPOGRAPHY HIERARCHY:
        1. PRIMARY FONT: {fonts[0] if fonts else 'Arial, sans-serif'} - Use for main content and body text
        2. HEADING FONT: {fonts[1] if len(fonts) > 1 else fonts[0] if fonts else 'Arial, sans-serif'} - Use for headers and titles
        3. ACCENT FONT: {fonts[2] if len(fonts) > 2 else fonts[0] if fonts else 'Arial, sans-serif'} - Use for special elements
        
        FONT RENDERING INSTRUCTIONS (CRITICAL FOR VISUAL FIDELITY):
        1. Use the EXACT same font families in the same order as specified above
        2. Include proper fallback fonts that match the general style (serif vs sans-serif)
        3. Match font weights PRECISELY - pay special attention to this as browsers render weights differently
        4. Match font sizes to the pixel - use exact px, em, or rem values from the original
        5. Preserve line heights and letter spacing exactly as in the original
        6. Use @font-face for any custom fonts or Google Fonts imports as in the original
        7. Apply the same font-feature-settings if any are used in the original
        8. Preserve any font smoothing settings (e.g., -webkit-font-smoothing, -moz-osx-font-smoothing)
        9. Match text-transform properties (uppercase, lowercase, capitalize) exactly
        10. Pay special attention to font rendering in headings vs body text
        
        ### LAYOUT SYSTEM
        GRID SYSTEM: {"Yes" if structure.get("layout", {}).get("grid_systems", False) else "No"}
        FLEXBOX USAGE: {"Yes" if structure.get("layout", {}).get("flexbox_usage", False) else "No"}
        CONTAINER COUNT: {structure.get("layout", {}).get("containers", 0)}
        
        ### COMPONENT IDENTIFIERS
        KEY CLASSES: {', '.join(important_classes) if important_classes else 'No specific classes identified'}
        IMPORTANT IDs: {', '.join(important_ids) if important_ids else 'No specific IDs identified'}
        VIEWPORT SETTINGS: {meta_tags if meta_tags else 'Not specified'}
        
        ### VISUAL PATTERNS & SPACING SYSTEM
        CONSISTENT PADDINGS: Extract consistent padding values and apply them throughout the clone
        MARGIN PATTERNS: Look for repeated margin patterns in similar components
        BORDER RADII: Identify common border radius values used across components
        SHADOW STYLES: Note shadow depth, spread, and color patterns
        
        ### COMPONENT ANALYSIS
        NAVIGATION: Identify the main navigation pattern (horizontal/vertical, dropdown style)
        BUTTONS: Extract button styles, hover states, and size variations
        CARDS/CONTAINERS: Identify card/container styling patterns (borders, shadows, padding)
        LISTS: Note how lists are styled and structured
        MEDIA: How images and other media are presented
        
        ### RESPONSIVE BEHAVIOR
        BREAKPOINTS: Identify major breakpoint patterns
        MOBILE ADAPTATION: How components transform at different screen sizes
        
        ## DOM STRUCTURE INSIGHTS
        {dom_structure if dom_structure else 'Standard DOM hierarchy'}
        
        ## FULL PAGE STRUCTURE (JSON)
        ```json
        {structure_info}
        ```
        
        ## IMAGE REFERENCES (maintain exact dimensions and positions):
        {json.dumps(important_imgs, indent=2) if important_imgs else 'No specific images found'}
        
        ## ORIGINAL HTML (for structural reference)
        ```html
        {html_snippet}
        ```
        
        ## COMPILED CSS (critical for exact styling)
        ```css
        {combined_css[:10000]}
        ```
        
        ## STRUCTURED REASONING WORKFLOW (FOLLOW THIS STEP-BY-STEP)

        ### PHASE 1: DESIGN SYSTEM EXTRACTION
        First, analyze the HTML and CSS to identify the underlying design system:
        1. Extract the COMPLETE typography system (font families, sizes, weights, line heights)
        2. Identify the color system (primary, secondary, accent colors)
        3. Catalog spacing patterns (margin, padding rhythms)
        4. Detect component patterns (buttons, cards, navigation, etc.)
        5. Map the responsive breakpoints and layout shifts

        ### PHASE 2: DOM STRUCTURE PLANNING
        Develop a clear mental model of the document structure:
        1. Map the primary layout containers and their relationships
        2. Identify repeating component patterns
        3. Note the exact nesting hierarchy of elements
        4. Plan how to preserve ALL original class names and IDs

        ### PHASE 3: CONTENT PRESERVATION (HIGHEST PRIORITY)
        You MUST include ALL textual content from the original page including:
        - ALL news titles, headlines, and story links in their ENTIRETY (no truncation)
        - ALL comments, user posts, descriptions, and article summaries
        - ALL points, vote counts, timestamps, and user information
        - ALL list items, navigation links, and footer text
        - EVERY SINGLE word, number, character, and punctuation mark
        - ALL links with their exact text content and href attributes
       
        DO NOT abbreviate, summarize, truncate or omit ANY textual content. This site has a lot of content - YOUR RESPONSE MUST BE COMPREHENSIVE to capture it all.
        
        ### PHASE 4: STYLING IMPLEMENTATION
        Implement the styling with extreme precision:
        1. Match typography perfectly - exact font families, sizes, weights, line heights
        2. Replicate color fidelity - exact hex/RGB/HSL values for all elements
        3. Preserve spacing precision - exact margins, paddings, positions
        4. Clone component styling - buttons, forms, cards must look identical
        5. Maintain responsive behavior - same breakpoints and adaptations
        
        9. USE SEMANTIC HTML - Proper heading hierarchy (h1-h6), lists (ul/ol), and sectioning elements (header, nav, main, section, article, aside, footer).
        
        10. MAINTAIN ACCESSIBILITY - Keep all aria attributes and roles for accessibility support.
        
        11. OPTIMIZE CSS - Include all necessary styles but avoid redundancy. Group related styles for readability.
        
        12. HANDLE SPECIAL ELEMENTS - Icons, SVGs, dividers, badges, tooltips must match original styling.
        
        13. DO NOT TRUNCATE OR OMIT CONTENT - Include ALL list items, paragraphs, and text blocks fully. Do not add ellipses or shorten content in any way.
        
        ### PHASE 5: FINAL OUTPUT CONSTRUCTION
        
        1. STRUCTURE:
           - START with <!DOCTYPE html> and NOTHING before it
           - CREATE complete <head> section with all meta tags, title, and viewport settings
           - ORGANIZE the document with proper nesting and section divisions
           - MAINTAIN semantic structure while preserving all classes and IDs
        
        2. STYLING:
           - PLACE all CSS in a <style> tag inside the <head> element
           - ORGANIZE CSS by component types for better maintainability
           - INCLUDE all pseudo-classes (hover, active, focus) for interactive elements
           - ADD all necessary media queries for responsive behavior
           - INCLUDE font imports or @font-face declarations as needed
        
        3. CONTENT INTEGRITY:
           - VERIFY all text content from the original is preserved verbatim
           - CONFIRM all list items and repeating elements are included (no truncation)
           - ENSURE all links have proper href attributes and text content
           - CHECK that all structural elements maintain their relationships
        
        ## CRITICAL OUTPUT REQUIREMENTS:
        
        - OUTPUT only valid HTML with embedded CSS - no external dependencies
        - INCLUDE all meta tags and correct viewport settings
        - PRESERVE every piece of text content from the original site
        - MATCH typography, colors, and spacing with pixel-perfect precision
        - DO NOT include any JavaScript or script tags
        - DO NOT include explanations or markdown - JUST THE HTML document
        - MAKE the output a complete, ready-to-render HTML document
        - FOCUS on creating a visually identical clone of the original site
        
        Remember: The PRIMARY goal is to create a visually indistinguishable clone that preserves ALL content and styling of the original website. Your output will be rendered in a browser and compared side-by-side with the original for assessment.
        """
        
        return prompt
        
    def _optimize_scrape_data(self, scrape_data: Dict[str, Any]) -> None:
        """
        Optimize the scrape data to reduce prompt size and improve response time
        """
        # Limit the number of assets to include in the prompt
        if "assets" in scrape_data and isinstance(scrape_data["assets"], dict):
            # Keep summary but limit individual asset lists
            for asset_type in ["images", "icons", "svgs", "videos", "audio", "fonts", "other_media"]:
                if asset_type in scrape_data["assets"] and len(scrape_data["assets"][asset_type]) > 10:
                    # Keep only the first 10 items of each type
                    scrape_data["assets"][asset_type] = scrape_data["assets"][asset_type][:10]
                    
        # Limit the amount of HTML included (often very large)
        if "html" in scrape_data and len(scrape_data["html"]) > 20000:
            # Keep first 10K and last 10K characters which usually contain the most important structure
            scrape_data["html"] = scrape_data["html"][:10000] + "\n...\n" + scrape_data["html"][-10000:]
            
        # Limit CSS content if very large
        if "css" in scrape_data and isinstance(scrape_data["css"], list) and len(scrape_data["css"]) > 5:
            # Keep only first 5 CSS items
            scrape_data["css"] = scrape_data["css"][:5]
            
        # Limit JS content as it's less important for visual cloning
        if "js" in scrape_data and isinstance(scrape_data["js"], list) and len(scrape_data["js"]) > 2:
            # Only keep information about the first 2 JS files
            scrape_data["js"] = scrape_data["js"][:2]
    
    def _extract_html_from_response(self, response_text: str) -> str:
        """
        Extract complete HTML from the LLM response and ensure it's valid while preserving all content
        """
        # For debugging
        print(f"Raw LLM response length: {len(response_text)}")
        
        # Check if the response is already valid HTML
        if response_text.strip().startswith("<!DOCTYPE html>") or response_text.strip().startswith("<html"):
            html_content = response_text
        else:
            # Look for HTML content in the response
            html_start = response_text.find("<!DOCTYPE html>")
            if html_start == -1:
                html_start = response_text.find("<html")
            
            if html_start == -1:
                # If no DOCTYPE or html tag, wrap the whole response in HTML tags
                html_content = f"<!DOCTYPE html>\n<html>\n<head>\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n</head>\n<body>\n{response_text}\n</body>\n</html>"
            else:
                # Extract from the start of the HTML
                html_content = response_text[html_start:]
        
        print(f"Extracted HTML content length: {len(html_content)}")
        
        # Check if the HTML has a closing </html> tag
        if "</html>" not in html_content:
            # If there's no closing tag, add one if we have an opening tag
            if "<html" in html_content and "</body>" in html_content:
                html_content += "</html>"
            elif "<html" in html_content:
                html_content += "</body></html>"
        
        # Add viewport meta tag if not present
        if "<meta" not in html_content and "<head>" in html_content:
            viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            html_content = html_content.replace("<head>", f"<head>\n    {viewport_meta}")
        
        # Ensure we have a <body> tag
        if "<body" not in html_content and "<html" in html_content:
            html_content = html_content.replace("</head>", "</head>\n<body>")
        
        # Try to clean/validate the HTML using BeautifulSoup with careful parsing
        try:
            from bs4 import BeautifulSoup
            # Choose either html.parser or html5lib, not both
            try:
                # First try with html5lib for better parsing
                import html5lib
                soup = BeautifulSoup(html_content, features="html5lib")
                print("Using html5lib parser")
            except ImportError:
                # Fallback to html.parser
                soup = BeautifulSoup(html_content, features="html.parser")
                print("Using html.parser")
            
            # Get the HTML without prettifying to keep original formatting
            html_content = str(soup)
            print(f"Parsed HTML content length after BeautifulSoup: {len(html_content)}")
        except Exception as e:
            print(f"Warning: Could not parse HTML with BeautifulSoup: {e}")
            # If BeautifulSoup parsing fails, return the original HTML content
        
        return html_content
    
    def _truncate_html(self, html: str, max_length: int = 20000) -> str:
        """
        Truncate HTML to a reasonable size while trying to maintain valid structure
        """
        if len(html) <= max_length:
            return html
        
        # Simple truncation approach - a more sophisticated version would
        # ensure we don't break in the middle of a tag
        truncated = html[:max_length]
        
        # Close any open tags
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(truncated, "lxml")
            return str(soup)
        except:
            # If BeautifulSoup parsing fails, return the simple truncation
            return truncated + "\n<!-- HTML truncated due to length -->"

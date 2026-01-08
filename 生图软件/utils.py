import os
import google.generativeai as genai
from PIL import Image, ImageOps, ImageDraw
import io
import re
import json

def configure_api(api_key):
    """Configures the Google Generative AI SDK."""
    if not api_key:
        raise ValueError("API Key is required.")
    genai.configure(api_key=api_key)

def get_available_models():
    """
    Dynamically lists models from the API.
    """
    try:
        # We need an API key to list models. config() might not have been called yet if just starting app.
        # But app.py calls this before configure_api with user input usually.
        # IF we have env var, we can try.
        if os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            
        models = list(genai.list_models())
        # Filter for generation models
        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods or 'generateImages' in m.supported_generation_methods]
        
        # Sort to put newest/best on top (heuristic)
        model_names.sort(reverse=True) 
        
        # Ensure we have the user's request if it's missing but valid?
        # If it's not in the list, it's not available.
        
        if not model_names:
            return [
                "gemini-3-pro-image-preview",
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash"
            ]
            
        # Clean names
        clean_names = [n.replace("models/", "") for n in model_names]
        
        # Strict Filter: Only show models we care about
        # User requested to delete most unusable models and keep gemini-3-pro-image-preview
        whitelist = [
            "gemini-3-pro-image-preview",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash-latest"
        ]
        
        # Filter: Keep if it STARTS with any whitelist item (to allow versions) or IS exactly a whitelist item
        # Actually simplest is just to return the intersection or just the whitelist if we want to force them.
        # But if the user doesn't have access to one, maybe we shouldn't show it?
        # Actually, user wants to see "gemini-3-pro-image-preview".
        
        filtered = [n for n in clean_names if any(w in n for w in whitelist)]
        
        # If filtering removed everything (unlikely), return fallbacks or at least standard ones
        if not filtered:
             return whitelist
             
        # Sort to put whitelist priority at top
        final_list = sorted(filtered, key=lambda x: (
            0 if "gemini-3-pro-image-preview" in x else
            1 if "gemini-2.0-flash-exp" in x else
            2 if "gemini-1.5-pro" in x else
            3
        ))
        
        return final_list
        
    except Exception as e:
        # Fallback if listing fails
        return [
            "gemini-3-pro-image-preview",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]

def get_best_vision_model():
    """
    Finds a working vision model from the available list.
    """
    try:
        models = get_available_models()
        # Preference list
        preferences = ["gemini-3-pro-image-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro"]
        
        for pref in preferences:
            for m in models:
                if pref in m:
                    return m
        return "gemini-1.5-flash" # Default fallback
    except:
        return "gemini-1.5-flash"


def add_white_padding(image, top_pixels=400):
    """
    Adds white padding to the top of the image.
    Returns: PIL Image
    """
    w, h = image.size
    new_h = h + top_pixels
    new_img = Image.new("RGB", (w, new_h), (255, 255, 255))
    # Paste original at the bottom
    new_img.paste(image, (0, top_pixels))
    return new_img

def add_white_padding_all(image, top=0, right=0, bottom=0, left=0):
    w, h = image.size
    new_w = w + left + right
    new_h = h + top + bottom
    new_img = Image.new("RGB", (new_w, new_h), (255, 255, 255))
    new_img.paste(image, (left, top))
    return new_img

def place_on_white_square(image, side=1024, margin_ratio=0.15):
    img = image.convert("RGBA")
    inner = int(side * max(0.0, 1.0 - 2.0 * margin_ratio))
    if inner <= 0:
        inner = side
    scale = min(inner / img.width, inner / img.height)
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    x = (side - resized.width) // 2
    y = (side - resized.height) // 2
    canvas.paste(resized, (x, y), resized)
    return canvas

def generate_model_character(prompt, pose_image=None, model_name="imagen-3.0-generate-001", target_size=(2048, 2048)):
    """
    Generates a character.
    If pose_image is provided, it uses it as a reference (Image Prompting).
    Output is strictly instructed to be on white background.
    """
    # Enhanced Prompt Construction
    # Force "Upper Body" and "White Background" (though we do BG removal later, it helps)
    full_prompt = (
        f"Professional Beauty Photography, extreme close-up headshot. {prompt}. "
        f"Lighting conditions: Soft light source from the top-right corner, illuminating the model continuously. "
        f"Consistent light direction and intensity. Soft but clear lighting, no overexposure. "
        f"Shadows on the model must be soft and diffuse, avoiding harsh contrast or deep heavy shadows. "
        f"Focus entirely on the face, skin texture, and makeup. "
        f"Output a Medium BUST PORTRAIT (Chest-up). "
        f"Plain white background. "
        f"Include HEAD, NECK, and SHOULDERS. Do NOT crop too tightly. "
        f"8k resolution, photorealistic, hyper-detailed."
    )
    
    print(f"Generating Model with Prompt: {full_prompt}")
    
    try:
        # NOTE: Using image_generation model directly
        from google.generativeai import ImageGenerationModel
        imagen_model = ImageGenerationModel(model_name)
        
        # Explicitly ask for 1:1 aspect ratio if supported, or just generate
        response = imagen_model.generate_images(
            prompt=full_prompt,
            number_of_images=1
        )
        
        generated_img = response[0]
        
        # Post-process: Upscale to 2K if needed
        # Standard Imagen output is 1024x1024.
        # User wants 2K.
        if generated_img.size != target_size:
             generated_img = generated_img.resize(target_size, Image.Resampling.LANCZOS)
             
        return generated_img

    except Exception as e:
        raise Exception(f"Model Generation Failed: {e}")

def process_hat_on_model(base_model_path, hat_file, offset_x=0, offset_y=0, hat_scale=1.0):
    """
    Composites hat onto the saved model image.
    Returns:
    - composite: The 'Target Look' (Hat placed on person).
    - mask: The protection mask (Hat is protected).
    """
    base_img = Image.open(base_model_path).convert("RGBA")
    hat_img = Image.open(hat_file).convert("RGBA")
    
    # Scale Hat
    if hat_scale != 1.0:
        new_size = (int(hat_img.width * hat_scale), int(hat_img.height * hat_scale))
        hat_img = hat_img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Calculate Position (Center top area usually, but user adjusts with offsets)
    # Default: Centered horizontally, near the newly created top padding?
    # Remember we added 400px padding. So the head is likely below 400px.
    # Actually, the 400px IS for the hat. So the hat should go in that space?
    # Or implies high hat?
    # Let's center it horizontally, and put it at 'offset_y' (which defaults to 0 -> top of image).
    
    x = (base_img.width - hat_img.width) // 2 + offset_x
    y = offset_y # Default 0
    
    # Composite for visual
    composite = base_img.copy()
    composite.paste(hat_img, (x, y), hat_img)
    
    # Create Mask
    # We want to keep the HAT (Source) and the PERSON (Base).
    # We only want to generate/blend the connection?
    # Actually, if we want to "wear" it, the hat might cover hair.
    # We want to Regenerate the area AROUND the hat?
    # Simpler approach:
    # 1. Composite Hat on Person.
    # 2. Mask = Hat Alpha (Protect Hat).
    # 3. Inpaint Prompt: "Person wearing this hat".
    # Result: AI will redraw the person (potentially changing them) to fit the hat?
    # CONSTRAINT: "Save Model" -> "Same Person".
    # If we regenerate the person, it changes identity.
    # TRICK: We should protect the PERSON'S FACE too if we can.
    # For now, we only protect the HAT (Requested: "Maintain Hat pixel perfect").
    
    mask = Image.new("L", composite.size, 255) # White (Edit Everything)
    
    # Protect Hat (Black)
    hat_alpha = hat_img.split()[3]
    mask.paste(0, (x, y), hat_alpha)
    
    return composite, mask

def describe_pose(pose_image):
    """
    Uses a Vision model to describe the pose in detail.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content([
            "Describe the pose, body position, and angle of the person in this image in extreme detail. Focus ONLY on the pose (arms, legs, head direction) and camera angle. Keep it concise.",
            pose_image
        ])
        return response.text
    except Exception as e:
        print(f"Pose description failed: {e}")
        return ""

def analyze_hat_details(ref_images):
    """
    Analyzes multiple images of the hat to create a super-detailed description.
    ref_images: List of PIL Images.
    """
    if not ref_images:
        return ""
        
    try:
        # Dynamically find best available model
        v_model_name = get_best_vision_model()
        # print(f"Using Vision Model: {v_model_name}")
        model = genai.GenerativeModel(v_model_name)
        
        # Construct prompt content with all images
        content = ["Describe this hat item in extreme detail. Focus on material texture, stitching, logos, colors, lighting properties, and any unique wear or style. Combine details from all images into one comprehensive description."]
        content.extend(ref_images)
        
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        print(f"Hat analysis failed: {e}")
        return f"A detailed hat. Error analyzing refs: {e}"

def generate_model_character(prompt, pose_image=None, model_name="imagen-3.0-generate-001"):
    """
    Generates a character.
    Using standard GenerativeModel.generate_content.
    """
    pose_description = ""
    if pose_image:
        pose_description = describe_pose(pose_image)
        prompt = f"{prompt}. Pose and Angle: {pose_description}"
        
    full_prompt = (
        f"{prompt}. "
        f"Bust portrait (Medium Close-up). "
        f"Show the person from the chest up. MUST include full shoulders and entire head. "
        f"Do NOT do an extreme close-up. Ensure hair and chin are fully visible with margin. "
        f"Professional studio lighting, isolated on white background. "
        f"High resolution, 8k, photorealistic."
    )
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(full_prompt)
        
        # Check for image content in response
        # Gemini API returns images in parts usually if it's an image model
        if hasattr(response, 'parts') and response.parts:
             for part in response.parts:
                 if hasattr(part, 'inline_data') and part.inline_data:
                     # It's an image, we need to convert bytes to PIL
                     img = Image.open(io.BytesIO(part.inline_data.data))
                     
                     # Force 2K Output (2048x2048) without distortion
                     # Use ImageOps.fit to scale and center-crop to fill the square
                     if img.size != (2048, 2048):
                         img = ImageOps.fit(img, (2048, 2048), method=Image.Resampling.LANCZOS)
                         
                     return img
        
        # Fallback: maybe it returned a text url? 
        # Or maybe the SDK wraps it differently?
        # For 'imagen-3.0-generate-001', it hopefully aligns with generate_content returning image data.
        # If not, we might need requests. But let's try this first.
        
        # If no inline_data, maybe it didn't generate an image.
        raise Exception("No image data found in response. Ensure Model ID is an Image Generation model.")

    except Exception as e:
        raise Exception(f"Model Generation Failed: {e}")

def edit_image_with_mask(base_image, mask_image, prompt, model_name="imagen-3.0-generate-001"):
    """
    Edits image using GenerativeModel (Multimodal).
    We pass [prompt, base_image, mask_image] if supported, or rely on instructions.
    """
    try:
        model = genai.GenerativeModel(model_name)
        # Attempt to pass images for inpainting
        # Note: Inpainting support via generate_content varies.
        # We try passing prompt + images.
        response = model.generate_content([prompt, base_image, mask_image])
        
        if hasattr(response, 'parts'):
             for part in response.parts:
                 if hasattr(part, 'inline_data'):
                     return Image.open(io.BytesIO(part.inline_data.data))
                     
        raise Exception("No image data in edit response.")
    except Exception as e:
        raise Exception(f"Edit Failed: {e}")

def generate_image(prompt, model_name="imagen-3.0-generate-001"):
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if hasattr(response, 'parts'):
             for part in response.parts:
                 if hasattr(part, 'inline_data'):
                     return Image.open(io.BytesIO(part.inline_data.data))
        raise Exception("No image returned.")
    except Exception as e:
        raise Exception(f"Generate Failed: {e}")

import re
import json

def extract_json_from_text(text):
    """
    Attempts to extract a JSON block from text.
    Returns parsed dict or None.
    """
    try:
        # Match ```json ... ``` or just {...}
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Fallback: find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except:
        pass
    return None

def execute_client_commands(command_data, source_images):
    """
    Executes commands found in JSON data on source_images.
    Returns: list of PIL Images, list of log messages
    """
    results_imgs = []
    logs = []
    
    if not source_images:
        return [], ["No source images to process."]
        
    target_img = source_images[0] # Default to first image
    
    try:
        # 1. Image Crop
        # Expects: "image_crop": [left, top, right, bottom] OR [y_min, x_min, y_max, x_max] (Gemini dependent)
        # Based on user screen: [0, 0, 1024, 650] which looks like [left, top, right, bottom] pixel coords.
        if "image_crop" in command_data:
            coords = command_data["image_crop"]
            if len(coords) == 4:
                # Simple heuristic: PIL crop is (left, top, right, bottom)
                # Ensure integers
                c = [int(v) for v in coords]
                
                # Check bounds safety (optional but good)
                w, h = target_img.size
                c[0] = max(0, c[0])
                c[1] = max(0, c[1])
                c[2] = min(w, c[2])
                c[3] = min(h, c[3])
                
                cropped = target_img.crop(tuple(c))
                results_imgs.append(cropped)
                logs.append(f"Executed 'image_crop': {c}")
                
        # Future commands can be added here
        
    except Exception as e:
        logs.append(f"Command execution error: {e}")
        
    return results_imgs, logs

TOOLS_SYSTEM_INSTRUCTION = """
You have the ability to process images using Client-Side Tools. 
To use a tool, output a JSON block.

Supported Tools:
1. Image Crop: outputs a cropped version of the image.
   JSON Format: {"image_crop": [left, top, right, bottom]}
   - Coordinates are in PIXELS (integers).
   - [left, top, right, bottom] corresponds to the bounding box.
   
Example:
User: "Crop to the face"
Model: "I will crop the image to the face.
```json
{"image_crop": [100, 50, 400, 350]}
```"
"""

def run_direct_gemini_command(instructions, images, model_name, system_instruction=None, generation_config=None):
    """
    Executes a direct command to Gemini with optional system instructions and config.
    """
    try:
        # Merge System Instructions
        final_system_instruction = TOOLS_SYSTEM_INSTRUCTION
        if system_instruction:
            final_system_instruction += "\n\n" + system_instruction

        model = genai.GenerativeModel(model_name, system_instruction=final_system_instruction)
        content = [instructions]
        content.extend(images or [])
        
        response = model.generate_content(content, generation_config=generation_config)
        
        texts = []
        imgs = []
        
        # Robust parsing of parts
        if hasattr(response, 'parts'):
            for part in response.parts:
                if hasattr(part, 'text') and part.text:
                    texts.append(part.text)
                if hasattr(part, 'inline_data') and part.inline_data:
                    imgs.append(Image.open(io.BytesIO(part.inline_data.data)))
        
        # If parts were empty or we just want to ensure we got text (Legacy/Simple check)
        if not texts and not imgs:
            try:
                if response.text:
                    texts.append(response.text)
            except ValueError:
                feedback = "Response was blocked by safety filters."
                if hasattr(response, 'prompt_feedback'):
                    feedback += f"\nFeedback: {response.prompt_feedback}"
                texts.append(feedback)

        # --- Auto-Execute Logic ---
        # If we have text, check for JSON commands
        if texts and images: # Only if we have source images to act on
            combined_text = "\n".join(texts)
            cmd_data = extract_json_from_text(combined_text)
            if cmd_data:
                processed_imgs, logs = execute_client_commands(cmd_data, images)
                if processed_imgs:
                    imgs.extend(processed_imgs)
                    texts.append("\n\n**System Execution Log:**\n" + "\n".join(logs))
                

        return texts, imgs
        
    except Exception as e:
        return [f"Error executing command: {str(e)}"], []

def get_object_mask(image, prompt="hat", model_name="gemini-2.0-flash-exp"):
    """
    Generates a mask and optional main-body bounding box using Gemini.
    Returns: (mask_pil, box_2d_tuple_or_None)
    """
    candidate_models = [model_name]
    # Fallback Priority: Gemini 2.0 (Best Vision) -> 1.5 Pro (Stable). 
    # Removed 1.5-flash due to API 404 errors.
    fallback_pool = ["gemini-2.0-flash-exp", "gemini-1.5-pro"]
    for m in fallback_pool:
        if m != model_name:
            candidate_models.append(m)
            
    last_error = None
    
    for curr_model in candidate_models:
        try:
            # print(f"Trying mask generation with: {curr_model}")
            model = genai.GenerativeModel(curr_model)
            
            # Dynamic Prompting based on Object Type
            is_hat = "hat" in prompt.lower() or "cap" in prompt.lower()
            
            if is_hat:
                # HAT SPECIALIZED PROMPT (Focus on Brim/Rigid Body)
                mask_prompt = (
                    f"1. Analyze the '{prompt}' in this image. Identify the 'Rigid Body/Brim' specific area. \n"
                    f"2. Return the bounding box of this 'Rigid Body/Brim' as JSON: {{'box_2d': [ymin, xmin, ymax, xmax]}} (0-1000 scale).\n"
                    f"3. Return the EXACT OUTLINE of the WHOLE object as a polygon JSON: {{'boundary_polygon_2d': [[y, x], [y, x], ...]}} (0-1000 scale). "
                    f"   This is critical if image generation fails.\n"
                    f"4. Generate a high-contrast binary mask image for the WHOLE '{prompt}'. White=Object, Black=Background. Solid fill.\n"
                )
            else:
                # GENERIC / PERSON PROMPT (Focus on Main Subject)
                mask_prompt = (
                    f"1. Analyze the '{prompt}' in this image. Identify the Main Subject.\n"
                    f"2. Return the bounding box of the Main Subject as JSON: {{'box_2d': [ymin, xmin, ymax, xmax]}} (0-1000 scale).\n"
                    f"3. Return the EXACT SILHOUETTE OUTLINE of the '{prompt}' as a polygon JSON: {{'boundary_polygon_2d': [[y, x], [y, x], ...]}} (0-1000 scale). "
                    f"   Trace the outer edge precisely. Include hair, shoulders, and head.\n"
                    f"4. Generate a high-contrast binary mask image for the '{prompt}'. White=Subject, Black=Background. Solid fill, no holes.\n"
                )
            
            response = model.generate_content([mask_prompt, image])
            
            mask_img = None
            bbox = None
            polygon = None
            text_segments = []
            
            # Robust Parsing
            if hasattr(response, 'parts'):
                 for part in response.parts:
                     if hasattr(part, 'inline_data') and part.inline_data:
                         try:
                            mask_img = Image.open(io.BytesIO(part.inline_data.data)).convert("L")
                         except Exception as e:
                            print(f"Image part decode failed: {e}")
                     
                     try:
                         if hasattr(part, 'text') and part.text:
                             text_segments.append(part.text)
                     except:
                         pass
            
            # Parse Text for BBox and Polygon
            full_text = "\n".join(text_segments)
            if full_text:
                json_data = extract_json_from_text(full_text)
                if json_data:
                    if 'box_2d' in json_data:
                        bbox = json_data['box_2d']
                    if 'boundary_polygon_2d' in json_data:
                        polygon = json_data['boundary_polygon_2d']
            
            # Fallback Strategy
            if not mask_img:
                 # print("Warning: No mask image returned. Attempting fallback to Polygon.")
                 if polygon:
                     # Draw Mask from Polygon
                     w, h = image.size
                     mask_img = Image.new("L", (w, h), 0)
                     draw = ImageDraw.Draw(mask_img)
                     # Convert 0-1000 points to pixels (point is [y, x])
                     # PIL Polygon expects [(x,y), (x,y)...]
                     pixels = []
                     for p in polygon:
                         y, x = p
                         px = int((x / 1000.0) * w)
                         py = int((y / 1000.0) * h)
                         pixels.append((px, py))
                     
                     if len(pixels) > 2:
                        # Draw polygon filled
                        draw.polygon(pixels, fill=255)
                 else:
                     raise Exception("Failed to generate mask image AND polygon.")
            
            # If we reached here, we have a mask_img (either from AI or polygon)
            return mask_img, bbox
            
        except Exception as e:
            print(f"Model {curr_model} failed for mask: {e}")
            last_error = e
            continue # Try next model
            
    # If all fail
    raise last_error if last_error else Exception("All models failed to generate mask.")

def cutout_object(image, mask):
    """
    Applies the mask to the image to create a transparent cutout.
    """
    if mask.mode != "L":
        mask = mask.convert("L")
        
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.Resampling.NEAREST)
    
    img_rgba = image.convert("RGBA")
    img_rgba.putalpha(mask)
    return img_rgba

def place_on_white_square_2k(image_rgba, side=2048, margin_ratio=0.10, focus_bbox=None):
    """
    Centers the RGBA image on a white square canvas.
    focus_bbox: [ymin, xmin, ymax, xmax] (0-1000 scale) of the "Main Body" to center.
                If None, centers the entire image bounding box.
    """
    w_orig, h_orig = image_rgba.size
    
    # 1. Get the bounding box of the ACTUAL VISIBLE PIXELS (The full cutout)
    full_content_bbox = image_rgba.getbbox() # (left, top, right, bottom)
    if not full_content_bbox:
        return Image.new("RGB", (side, side), (255, 255, 255))
        
    l_full, t_full, r_full, b_full = full_content_bbox
    w_full = r_full - l_full
    h_full = b_full - t_full
    
    # Crop to the full content
    cropped_full = image_rgba.crop(full_content_bbox)
    
    # Define the "Focus Area" within this cropped image
    if focus_bbox:
        ymin, xmin, ymax, xmax = focus_bbox
        # Convert 0-1000 to pixels in ORIGINAL space
        f_top = (ymin / 1000.0) * h_orig
        f_left = (xmin / 1000.0) * w_orig
        f_bottom = (ymax / 1000.0) * h_orig
        f_right = (xmax / 1000.0) * w_orig
        
        # Map to CROPPED space
        cf_top = f_top - t_full
        cf_left = f_left - l_full
        cf_bottom = f_bottom - t_full
        cf_right = f_right - l_full
        
        # Validate/Clamp
        cf_top = max(0, cf_top)
        cf_left = max(0, cf_left)
        cf_bottom = min(h_full, cf_bottom)
        cf_right = min(w_full, cf_right)
        
        cf_w = cf_right - cf_left
        cf_h = cf_bottom - cf_top
        
        # Use focus rect if valid area
        if cf_w > 0 and cf_h > 0:
             focus_rect = (cf_left, cf_top, cf_w, cf_h)
        else:
             focus_rect = (0, 0, w_full, h_full)
    else:
        focus_rect = (0, 0, w_full, h_full)
        
    # focus_rect is (x, y, w, h) relative to cropped_full
    fx, fy, fw, fh = focus_rect
    
    # 2. Determine SCALE
    # Strategy: Fit the FULL object within margins, maximizing size.
    inner_side = int(side * (1 - 2 * margin_ratio))
    scale = min(inner_side / w_full, inner_side / h_full)
    
    # Resize
    new_w_full = int(w_full * scale)
    new_h_full = int(h_full * scale)
    resized_full = cropped_full.resize((new_w_full, new_h_full), Image.Resampling.LANCZOS)
    
    # 3. Determine POSITION (Centering Logic)
    # Center of canvas
    cx_canvas = side // 2
    cy_canvas = side // 2
    
    # Center of Focus Area (scaled)
    fx_new = fx * scale
    fy_new = fy * scale
    fw_new = fw * scale
    fh_new = fh * scale
    
    cx_focus = fx_new + fw_new / 2
    cy_focus = fy_new + fh_new / 2
    
    # Calculate Paste Position (Top Left)
    # canvas_center = paste_pos + focus_center
    paste_x = int(cx_canvas - cx_focus)
    paste_y = int(cy_canvas - cy_focus)
    
    # 4. Paste
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    canvas.paste(resized_full, (paste_x, paste_y), resized_full)
    
    return canvas.convert("RGB")

def remove_background(image, prompt="person", model_name="gemini-2.0-flash-exp"):
    """
    Removes background from a person/model image and places them on a white background.
    Returns: PIL Image (RGB) on white background.
    """
    try:
        # Use the robust mask generation function
        mask_img, _ = get_object_mask(image, prompt=prompt, model_name=model_name)
        
        if not mask_img:
            raise Exception("Models failed to generate mask via get_object_mask.")
            
        # Ensure mask matches image size
        if mask_img.size != image.size:
             mask_img = mask_img.resize(image.size, Image.Resampling.NEAREST)
             
        # Create Cutout
        img_rgba = image.convert("RGBA")
        
        # Composite
        # 1. Background White
        bg = Image.new("RGB", img_rgba.size, (255, 255, 255))
        # 2. Paste using mask
        bg.paste(img_rgba, (0, 0), mask_img)
        
        return bg
        
    except Exception as e:
        print(f"Remove background error: {e}")
        # Return original if failed? No, improved UI handles error.
        raise e

def smart_crop_headshot(image, model_name="gemini-2.0-flash-exp"):
    """
    Intelligently crops the image to a "Head and Shoulders" portrait and upscales to 2K.
    """
    candidate_models = [model_name]
    fallback_pool = ["gemini-2.0-flash-exp", "gemini-1.5-pro"]
    for m in fallback_pool:
        if m != model_name:
            candidate_models.append(m)
            
    last_error = None
    
    for curr_model in candidate_models:
        try:
            # print(f"Trying smart crop with: {curr_model}")
            model = genai.GenerativeModel(curr_model)
            
            # Prompt for Headshot BBox
            prompt = (
                "Analyze this image. I need a standard 'Passport Style' layout. "
                "Identify the bounding box that includes the ENTIRE HEAD (hair to chin) AND THE SHOULDERS (upper chest). "
                "It is CRITICAL to include the shoulders. Do NOT crop tightly around the face. "
                "Return the bounding box as JSON: {'box_2d': [ymin, xmin, ymax, xmax]} where coordinates are normalized 0-1000."
            )
            
            response = model.generate_content([prompt, image])
            
            bbox = None
            if response.text:
                 json_data = extract_json_from_text(response.text)
                 if json_data and 'box_2d' in json_data:
                     bbox = json_data['box_2d']
            
            if not bbox:
                # print(f"Model {curr_model} did not return bbox.")
                raise Exception("No bbox returned.")
            
            # If successful, Proceed to Crop Logic (Break loop)
            # ... Crop Logic Below needs to be indented or moved out ...
            # To keep diff clean, I'll put crop logic AFTER the loop, storing result in `final_bbox`
            
            final_bbox = bbox
            break # Success!
            
        except Exception as e:
            print(f"Smart crop model {curr_model} failed: {e}")
            last_error = e
            continue
            
    if 'final_bbox' not in locals():
         # Fallback Heuristic if ALL models fail
         print("All smart crop models failed. Using heuristic fallback.")
         final_bbox = [50, 150, 850, 850] # Safe center crop
         
    # Execute Crop with final_bbox
    w, h = image.size
    ymin, xmin, ymax, xmax = final_bbox
    
    # --- ADD SAFETY PADDING ---
    # Gemini BBoxes can be very tight. We expand them to ensure no cutout of hair/shoulders.
    # Scale is 0-1000.
    pad_top = 200   # 20% top padding (Increased for big hair)
    pad_side = 100  # 10% side padding (Ensure shoulders)
    pad_bottom = 100 # 10% bottom
    
    ymin = max(0, ymin - pad_top)
    xmin = max(0, xmin - pad_side)
    xmax = min(1000, xmax + pad_side)
    ymax = min(1000, ymax + pad_bottom)
    
    # Convert to pixels
    top = int((ymin / 1000.0) * h)
    left = int((xmin / 1000.0) * w)
    bottom = int((ymax / 1000.0) * h)
    right = int((xmax / 1000.0) * w)
    
    # Validate/Clamp
    top = max(0, top)
    left = max(0, left)
    bottom = min(h, bottom)
    right = min(w, right)
    
    if (right - left) < 50 or (bottom - top) < 50:
         raise Exception("Identified crop area is too small.")
             
    # TIGHT CROP (based on BBox)
    # Note: BBox is usually tight on head/shoulders.
    headshot_crop = image.crop((left, top, right, bottom))
    
    # LAYOUT ON 2K CANVAS
    # Spec: Top 400px blank. Left/Right 100px blank.
    # Canvas: 2048x2048 White
    final_canvas = Image.new("RGB", (2048, 2048), (255, 255, 255))
    
    target_width = 2048 - 100 - 100  # 1848
    
    # Calculate height maintaining aspect ratio
    w_orig, h_orig = headshot_crop.size
    ratio = target_width / w_orig
    target_height = int(h_orig * ratio)
    
    # Resize crop
    resized_crop = headshot_crop.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Paste: X=100, Y=400
    # If the resized image is taller than available space (2048-400=1648), it will crop at bottom.
    # This is expected for "Portrait" where we prioritize Head position.
    final_canvas.paste(resized_crop, (100, 400))
    
    return final_canvas




def flexible_edit_image(image, instruction, references=None, model_name="gemini-2.0-flash-exp"):
    """
    Direct instruction-based image editing (Nanobanana Pro2 Mode).
    Maintains exact input resolution.
    Accepts optional reference images.
    """
    candidate_models = [model_name]
    fallback_pool = ["gemini-3-pro-image", "gemini-3-pro-image-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro"]
    for m in fallback_pool:
        if m != model_name:
            candidate_models.append(m)

    last_error = None
    
    for curr_model in candidate_models:
        try:
            model = genai.GenerativeModel(curr_model)
            
            ref_note = ""
            if references:
                ref_note = (
                    "IMPORTANT: The FIRST image provided below is the TARGET image to edit. "
                    "All SUBSEQUENT images are REFERENCE materials (style/object source). "
                    "Apply the details/style from the reference images to the target image according to the instruction. "
                )
            
            prompt = (
                f"{ref_note}"
                f"Instruction: {instruction}. "
                f"Output the modified target image only. "
                f"Strictly maintain resolution and composition of the target image."
            )
            
            # Construct content list
            # [prompt, main_image, ref1, ref2, ...]
            content = [prompt, image]
            if references:
                content.extend(references)
            
            # Call model
            response = model.generate_content(content)
            
            generated_img = None
            if hasattr(response, 'parts'):
                 for part in response.parts:
                     if hasattr(part, 'inline_data') and part.inline_data:
                         try:
                            generated_img = Image.open(io.BytesIO(part.inline_data.data))
                         except:
                            pass
                         break
                         
            if not generated_img:
                error_msg = "Model returned no image."
                if hasattr(response, 'text') and response.text:
                    error_msg += f" Response text: {response.text}"
                raise Exception(error_msg)
                
            # FORCE ORIGINAL SIZE/PIXELS
            if generated_img.size != image.size:
                generated_img = generated_img.resize(image.size, Image.Resampling.LANCZOS)
                
            return generated_img

        except Exception as e:
            print(f"Flexible edit failed with {curr_model}: {e}")
            last_error = e
            continue
            
    # If all fail
    raise last_error

def generate_random_prompt(model_name="gemini-2.0-flash-exp"):
    """
    Generates a creative, randomized prompt for a fashion model portrait.
    Returns: String (The prompt text)
    """
    try:
        model = genai.GenerativeModel(model_name)
        meta_prompt = (
            "Generate a creative and detailed text-to-image prompt for a high-end fashion model HEADSHOT / BEAUTY SHOT. "
            "Focus ONLY on the face, hair, and makeup. Do NOT describe clothing below the neck. "
            "Vary the gender, age, ethnicity, hair style, and lighting. "
            "Output ONLY the prompt text, no preamble or quotes."
        )
        
        response = model.generate_content(meta_prompt)
        if response.text:
            return response.text.strip().replace('"', '')
        return "A details close-up headshot of a professional fashion model, neutral expression"
        
    except Exception as e:
        print(f"Random prompt gen failed: {e}")
        return "A professional fashion model, front view, neutral expression"


from PIL import ImageOps

def reduce_shadows(image, mask_image, intensity="Soft", model_name="gemini-2.0-flash-exp"):
    """
    Reduces shadows in the masked area using Generative Fill.
    """
    # INVERT MASK: Gemini typically treats BLACK (0) as the area to edit (INPAINT), and WHITE (255) as valid/keep.
    # The canvas input is White=Drawn(Shadow), Black=Background.
    # So we Invert -> Black=Shadow(Edit), White=Background(Keep).
    if mask_image.mode != 'L':
        mask_image = mask_image.convert('L')
    mask_image = ImageOps.invert(mask_image)
    
    # Prompt engineering for shadow removal
    base_prompt = (
        "Inpaint/Regenerate task. "
        "The masked area is covered in unwanted shadow. "
        "REGENERATE the content within the mask to be fully illuminated by bright, soft, natural light. "
        "REMOVE THE SHADOW COMPLETELY. "
        "Ensure the skin/texture tone matches the bright parts of the image surrounding the mask. "
        "Seamless blend. Low contrast."
    )
    
    if intensity == "Strong":
        base_prompt += " Use high brightness. Erase all darkness."
    else:
        base_prompt += " Natural lighting adjustment."

    # Use the existing edit function
    return edit_image_with_mask(image, mask_image, base_prompt, model_name=model_name)

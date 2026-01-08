import streamlit as st
import utils
from PIL import Image
import os
import datetime
from dotenv import load_dotenv
from streamlit_drawable_canvas import st_canvas

load_dotenv()

st.set_page_config(page_title="Nano Banana 2 Pro - 图像生成工坊", layout="wide")

# Ensure models dir exists
if not os.path.exists("models"):
    os.makedirs("models")

st.title("🍌 Nano Banana 2 Pro - 高级图像工坊")

# Sidebar
with st.sidebar:
    st.header("设置")
    env_api_key = os.getenv("GOOGLE_API_KEY", "")
    api_key = st.text_input("Google API Key", value=env_api_key, type="password")
    
    default_models = utils.get_available_models()
    model_name = st.selectbox("模型选择 (Model ID)", default_models, index=0)
    if model_name == "Custom...":
        model_name = st.text_input("输入自定义模型 ID")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["✨ 创建模特", "🎩 戴帽子工坊", "🔍 细节修复/增强", "✂️ 智能抠图", "🍌 Nanobanana Pro2", "🛰️ Gemini 直控", "💡 光影调整"])

# ... [Tab 1 and Tab 2 code remains similar, ensure consistent indentation if replacing] ...
# (We will append Tab 3 code at the end of the file or replacing the Tabs definition)

# --- TAB 3: Standalone Enhancer ---
with tab3:
    st.header("第三步: 修复与增强细节")
    st.markdown("选择功能模式：")
    
    # Top-level Mode Selection
    tab3_mode = st.radio("功能选择", ["修复/增强模特身上的草帽 (Fix Hat on Model)", "单图增强 (Enhance Standalone Hat)"], horizontal=True)
    
    # Shared Inputs
    # api_key is already defined from the sidebar, no need to re-fetch from os.getenv here.
    
    # --- Mode 1: Fix Hat on Model (Existing Logic) ---
    if tab3_mode == "修复/增强模特身上的草帽 (Fix Hat on Model)":
        st.caption("上传带草帽的模特图，通过遮罩修复或增强特定区域。")
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            target_img_file = st.file_uploader("1. 带草帽的图片 (目标图)", type=["png", "jpg"], key="t3_target")
            
        with col_e2:
            mask_mode = st.radio("遮罩来源", ["应用内绘制", "上传遮罩文件"], horizontal=True)
            mask_pil = None
            if mask_mode == "上传遮罩文件":
                mask_img_file = st.file_uploader("2. 上传遮罩 (白色=草帽)", type=["png", "jpg"], key="t3_mask")
                if mask_img_file:
                    mask_pil = Image.open(mask_img_file).convert("L")
        
        # Canvas Logic (Same as before)
        if mask_mode == "应用内绘制" and target_img_file:
             st.info("请涂抹**草帽**区域。")
             from streamlit_drawable_canvas import st_canvas
             bg_image = Image.open(target_img_file).convert("RGBA")
             stroke_width = st.slider("笔刷大小", 1, 50, 20)
             canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 1.0)",
                stroke_width=stroke_width,
                stroke_color="#FFFFFF",
                background_image=bg_image,
                update_streamlit=True,
                height=600, width=600,
                drawing_mode="freedraw",
                key="canvas_mask",
             )
             if canvas_result.image_data is not None:
                 mask_data = canvas_result.image_data
                 mask_pil = Image.fromarray(mask_data.astype('uint8'), mode="RGBA").split()[3]
                 if mask_pil.size != bg_image.size:
                     mask_pil = mask_pil.resize(bg_image.size, Image.Resampling.NEAREST)
             if mask_pil:
                st.caption("已生成遮罩！")
                with st.expander("预览生成的遮罩"):
                    st.image(mask_pil)

    # --- Mode 2: Standalone Hat Enhancement ---
    else: 
        st.caption("直接上传单独的草帽图片（支持透明PNG），AI 将自动识别并增强材质细节。")
        target_img_file = st.file_uploader("上传草帽图片 (PNG推荐)", type=["png", "jpg", "jpeg"], key="t3_hat_only")
        
        # New Option: Smart Cutout
        use_smart_cutout = st.checkbox("增强后应用智能抠图 (Auto Cutout After Enhance)", value=False, help="勾选后，AI 将先基于原图进行材质增强（保留环境光），处理完成后自动移除背景。")
        
        mask_pil = None # This will be determined during processing
        
        if target_img_file:
            input_hat = Image.open(target_img_file).convert("RGBA")
            st.image(input_hat, caption="原图", width=300)
            
            # Smart Cutout Logic (Preview only, actual cutout happens on "开始处理")
            if use_smart_cutout and api_key:
                 if st.button("预览智能抠图效果"):
                     try:
                         utils.configure_api(api_key)
                         with st.spinner("正在智能移除背景..."):
                             # Use remove_background which returns RGBA
                             cutout_res = utils.remove_background(input_hat.convert("RGB"), prompt="hat", model_name="gemini-2.0-flash-exp")
                             st.image(cutout_res, caption="智能抠图预览", width=300)
                     except Exception as e:
                         st.error(f"抠图失败: {e}")

            # Auto-Mask Generation Visualization (Client side logic for preview)
            # Actual mask generation happens during processing or here.
            # If standard PNG with alpha.
            if input_hat.mode == "RGBA":
                mask_pil = input_hat.split()[3]
            else:
                mask_pil = Image.new("L", input_hat.size, 255)
            
            if mask_pil:
                st.caption("已生成遮罩！")
                with st.expander("预览生成的遮罩"):
                    st.image(mask_pil)
    
    st.markdown("---")
    
    # Common Controls
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if tab3_mode.startswith("单图"):
             process_mode = "材质细节增强 (Texture Enhance)"
             st.info("模式锁定: 材质细节增强")
        else:
             process_mode = st.radio("处理模式", ["标准修复 (Fix/Inpaint)", "材质细节增强 (Texture Enhance)"], help="材质增强用于提升清晰度且不改变结构。")
             
    with col_c2:
        extra_prompt_input = st.text_input("额外提示词 (可选)", help="例如: 'smoother edges', 'weaving texture'")

    enhancement_refs = st.file_uploader("参考细节图 (可选)", type=["png", "jpg"], accept_multiple_files=True, key="t3_refs")
    
    # Session State for Persistence
    if 'enhanced_result' not in st.session_state:
        st.session_state['enhanced_result'] = None

    if st.button("开始处理", type="primary"):
        if not target_img_file:
            st.error("请先上传图片。")
        elif not mask_pil and tab3_mode.startswith("修复"):
             st.error("修复模式需要遮罩。")
        elif not api_key:
            st.error("缺少 API Key")
        else:
            try:
                utils.configure_api(api_key)
                
                # 1. Analyze Details
                detail_text = ""
                if enhancement_refs:
                    with st.spinner("分析参考图..."):
                        ref_ps = [Image.open(f) for f in enhancement_refs]
                        detail_text = utils.analyze_hat_details(ref_ps)
                
                # 2. Prepare Target (Standalone specific logic)
                target_pil = Image.open(target_img_file).convert("RGB")
                
                if tab3_mode.startswith("单图"):
                     raw_input = Image.open(target_img_file).convert("RGBA")
                     
                     # B. 2K Upscale/Resize (First step)
                     max_dim = 2048
                     if max(raw_input.size) < max_dim:
                         ratio = max_dim / max(raw_input.size)
                         new_size = (int(raw_input.width * ratio), int(raw_input.height * ratio))
                         raw_input = raw_input.resize(new_size, Image.Resampling.LANCZOS)
                     elif max(raw_input.size) > max_dim:
                         if raw_input.width > max_dim or raw_input.height > max_dim:
                             ratio = max_dim / max(raw_input.size)
                             new_size = (int(raw_input.width * ratio), int(raw_input.height * ratio))
                             raw_input = raw_input.resize(new_size, Image.Resampling.LANCZOS)
                     
                     target_pil = raw_input.convert("RGB")
                     
                     # Generate Mask for Enhancement (and later Cutout)
                     # If Smart Cutout is requested, OR we don't have a good alpha mask (JPG), we rely on AI mask.
                     if use_smart_cutout or raw_input.mode != "RGBA" or not mask_pil:
                         with st.spinner("正在生成高精度遮罩..."):
                             # Calls the robust get_object_mask (with polygon fallback)
                             mask_pil, _ = utils.get_object_mask(target_pil, prompt="hat", model_name=model_name)
                     else:
                         # Use existing Alpha if available and Smart Cutout NOT requested
                         # (User wants to enhance existing cutout)
                         if raw_input.mode == "RGBA":
                             mask_pil = raw_input.split()[3]
                         else:
                             # Fallback for some reason
                             mask_pil = Image.new("L", target_pil.size, 255)
                
                # Ensure mask matches target size
                if mask_pil.size != target_pil.size:
                    mask_pil = mask_pil.resize(target_pil.size, Image.Resampling.NEAREST)
                
                # 3. Prompt Construction
                if "Texture Enhance" in process_mode:
                    enhance_prompt = (
                        f"High resolution, professional photography. "
                        f"Enhance the texture, clarity and details of the object to make it hyper-realistic 8k. "
                        f"DO NOT change the shape, structure, or key elements. "
                        f"Make edges smoother and defined. {extra_prompt_input}. "
                        f"Reference details: {detail_text}."
                    )
                else:
                    enhance_prompt = (
                        f"High resolution, professional photography. Fix and regenerate key area. "
                        f"Match style: {detail_text}. {extra_prompt_input}."
                    )
                
                # 4. Execute Enhancement (ON THE ORIGINAL BACKGROUND)
                with st.spinner("正在增强材质细节..."):
                    res = utils.edit_image_with_mask(target_pil, mask_pil, enhance_prompt, model_name)
                    
                    # Force Output Resolution to Match Input (2K)
                    # The model might return 1024x1024. We must upscale it back to target_pil size (2048x2048)
                    if res.size != target_pil.size:
                        res = res.resize(target_pil.size, Image.Resampling.LANCZOS)

                    # 5. Post-Process (Cutout AFTER Enhance)
                    if tab3_mode.startswith("单图"):
                         if use_smart_cutout:
                             # Apply the mask we generated to the ENHANCED result
                             res = utils.cutout_object(res, mask_pil)
                         else:
                             # Restore original alpha if it was a PNG upload and we just enhanced
                             if target_img_file.name.lower().endswith(".png"):
                                 res = res.convert("RGBA")
                                 res.putalpha(mask_pil)
                    
                    # Store in Session State
                    st.session_state['enhanced_result'] = res
                    
            except Exception as e:
                st.error(f"处理失败: {e}")

    # Display Persisted Result
    if st.session_state['enhanced_result']:
        st.success("处理完成！")
        st.image(st.session_state['enhanced_result'], caption="最终结果", use_container_width=True)
        
        import io
        buf = io.BytesIO()
        st.session_state['enhanced_result'].save(buf, format="PNG")
        st.download_button("下载结果 (PNG 2K)", buf.getvalue(), "enhanced_hat_2k.png", "image/png")

# --- TAB 4: Smart Cutout ---
with tab4:
    st.header("第四步: 智能抠图 (Smart Cutout)")
    st.markdown("利用 Gemini 强大的视觉理解能力，精确提取帽子并自动排版到 2K 白底画布。")
    
    col_c1, col_c2 = st.columns([1, 1])
    
    with col_c1:
        cutout_target_file = st.file_uploader("上传图片 (包含物体的图片)", type=["png", "jpg", "jpeg"], key="t4_target")
        
    with col_c2:
        target_object = st.text_input("要提取的物体 (Object)", value="Hat")
        # Custom model selector for this feature, prioritizing the user's request
        cutout_model = st.selectbox("模型 (Model)", ["gemini-3-pro-image-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"], index=0, help="Gemini 2.0 Flash Exp 通常具有出色的分割能力。")
    
    if st.button("提取并格式化", type="primary"):
        if not cutout_target_file:
            st.error("请先上传图片。")
        elif not api_key:
            st.error("缺少 API Key")
        else:
            try:
                utils.configure_api(api_key)
                
                with st.spinner("1/3 正在生成高精度掩码..."):
                    # 1. Get Mask & Brim BBox
                    input_pil = Image.open(cutout_target_file).convert("RGB")
                    # Use user prompt for object
                    mask_pil, brim_bbox = utils.get_object_mask(input_pil, prompt=target_object, model_name=cutout_model)
                    
                    # Debug: Show mask in expander
                    # with st.expander("Debug: View Generated Mask"):
                    #     st.image(mask_pil, caption="Generated Mask", width=300)
                        
                with st.spinner("2/3 正在抠取物体..."):
                    # 2. Cutout
                    cutout_rgba = utils.cutout_object(input_pil, mask_pil)
                    
                with st.spinner("3/3 正在格式化为 2K 方图... (以主体/帽檐为中心)"):
                    # 3. Format
                    # Pass the brim_bbox to center based on the rigid body
                    final_2k = utils.place_on_white_square_2k(cutout_rgba, side=2048, focus_bbox=brim_bbox)
                
                # Store in session state
                st.session_state['cutout_result_2k'] = final_2k
                st.success(f"处理完成! (居中策略: {'智能主体聚焦' if brim_bbox else '整体居中'})")
                
            except Exception as e:
                st.error(f"处理失败: {e}")

    # Display Result from Session State
    if 'cutout_result_2k' in st.session_state:
        st.image(st.session_state['cutout_result_2k'], caption="最终结果 (2K - 2048x2048)", width=600)
        
        # Download
        import io
        buf = io.BytesIO()
        st.session_state['cutout_result_2k'].save(buf, format="PNG")
        st.download_button(
            label="下载 2K 图片", 
            data=buf.getvalue(), 
            file_name="cutout_2k.png", 
            mime="image/png"
        )

# --- TAB 5: Nanobanana Editor ---
with tab5:
    st.header("🍌 Nanobanana Pro2 (Magic Editor)")
    st.markdown("直接指令编辑 - 保持像素级原图尺寸")
    
    col_n1, col_n2 = st.columns([1, 1])
    
    with col_n1:
        st.markdown("**1. 待处理图片 (Batch Input)**")
        nano_files = st.file_uploader("上传原图 (支持多选)", type=["png", "jpg", "jpeg"], key="nano_input", accept_multiple_files=True)
        
        st.divider()
        st.markdown("**2. 参考素材 (References)**")
        nano_refs = st.file_uploader("上传参考图/素材 (可选)", type=["png", "jpg", "jpeg"], key="nano_refs", accept_multiple_files=True)
        
    with col_n2:
        st.markdown("**3. 编辑指令 (Instruction)**")
        nano_instr = st.text_area("描述修改需求", placeholder="例如: 参照提供的帽子图，给模特戴上这款帽子。或者: 把背景改成第一张参考图的风格...", height=150)
        nano_model = st.selectbox("核心模型", ["gemini-3-pro-image", "gemini-3-pro-image-preview", "gemini-2.0-flash-exp", "gemini-1.5-pro"], index=0, key="nano_model")
        auto_save_lib = st.checkbox("自动保存到模特库 (Auto-save)", value=False, help="处理完成后自动将结果保存到 'models/' 文件夹")
        
    if st.button("🍌 执行 Nanobanana", type="primary"):
        if not nano_files:
            st.error("请先上传待处理图片")
        elif not nano_instr:
            st.error("请输入编辑指令")
        elif not api_key:
            st.error("缺少 API Key")
        else:
            try:
                utils.configure_api(api_key)
                
                # Load References once
                ref_imgs = []
                if nano_refs:
                    for rf in nano_refs:
                        ref_imgs.append(Image.open(rf).convert("RGB"))
                
                # Iterate over all uploaded files
                for idx, n_file in enumerate(nano_files):
                    st.divider()
                    st.markdown(f"**处理第 {idx+1}/{len(nano_files)} 张图片: {n_file.name}**")
                    
                    img_p = Image.open(n_file).convert("RGB")
                    
                    with st.spinner(f"Nanobanana 正在施法 ({n_file.name})..."):
                        # Process with references
                        res = utils.flexible_edit_image(img_p, nano_instr, references=ref_imgs, model_name=nano_model)
                        
                    # Show Side by Side
                    c1, c2 = st.columns(2)
                    with c1:
                        st.image(img_p, caption=f"原图 ({img_p.size})", use_container_width=True)
                    with c2:
                        st.image(res, caption=f"Nanobanana 结果 ({res.size})", use_container_width=True)
                        
                    # Download
                    import io
                    buf = io.BytesIO()
                    res.save(buf, format="PNG")
                    st.download_button(
                        label=f"下载结果 ({idx+1})", 
                        data=buf.getvalue(), 
                        file_name=f"nanobanana_edit_{idx+1}.png", 
                        mime="image/png",
                        key=f"dl_nano_{idx}"
                    )
                    
                    # Auto Update Session State for Preview elsewhere if needed? No.
                    
                    # Auto Save to Library
                    if auto_save_lib:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        save_name = f"models/nanobanana_{ts}_{idx+1}.png"
                        res.save(save_name)
                        st.caption(f"✅ 已保存到模特库: {save_name}")
                    
                st.success("所有图片处理完成！")
                
            except Exception as e:
                st.error(f"Nanobanana 失败: {e}")

# --- TAB 6: Direct Control ---
with tab6:
    st.header("Gemini/NanoBanana 直接控制台")
    
    col_d1, col_d2 = st.columns([2, 1])
    
    with col_d1:
        direct_prompt = st.text_area("指令 (Instructions)", "描述你希望 NanoBanana 做什么", height=150)
        direct_files = st.file_uploader("上传图片 (支持多张)", type=["png","jpg","jpeg"], accept_multiple_files=True, key="direct_imgs")
    
    with col_d2:
        with st.expander("🛠️ 高级设置", expanded=True):
            system_instr = st.text_area("系统指令 (System Instruction)", "", placeholder="例如: 你是一个海盗...", height=100)
            temperature = st.slider("温度 (Temperature)", 0.0, 2.0, 1.0, 0.1, help="越高越有创意，越低越确定")
            
    if st.button("运行指令", type="primary"):
        if not api_key:
            st.error("缺少 API Key")
        else:
            try:
                utils.configure_api(api_key)
                imgs = [Image.open(f) for f in (direct_files or [])]
                
                # Config
                gen_config = {"temperature": temperature}
                s_instruct = system_instr if system_instr.strip() else None
                
                with st.spinner("正在与 Gemini 通信..."):
                    texts, images = utils.run_direct_gemini_command(
                        direct_prompt, 
                        imgs, 
                        model_name, 
                        system_instruction=s_instruct, 
                        generation_config=gen_config
                    )
                
                if texts:
                    for t in texts:
                        st.markdown(t)
                        st.markdown("---")
                        
                if images:
                    st.subheader("生成的图片")
                    cols = st.columns(min(len(images), 3))
                    for i, im in enumerate(images):
                        with cols[i % 3]:
                            st.image(im, caption=f"输出 {i+1}", use_container_width=True)
                            import io
                            buf = io.BytesIO()
                            im.save(buf, format="PNG")
                            st.download_button(f"下载图 {i+1}", data=buf.getvalue(), file_name=f"direct_output_{i+1}.png", mime="image/png")
                
                if not texts and not images:
                    st.warning("模型未返回任何输出。")
                    
            except Exception as e:
                st.error(f"指令运行失败: {e}")
# --- TAB 1: Create Model ---
# --- TAB 1: Create Model ---
with tab1:
    st.header("第一步: 创建或定义模特")
    
    creation_mode = st.radio("模式", ["生成新模特", "上传现有图片"], horizontal=True)
    
    # --- Mode: Generate ---
    if creation_mode == "生成新模特":
        st.markdown("生成一个新的模特模板。系统会自动在头部上方添加留白。")
        col_p1, col_p2 = st.columns([2, 1])
        
        with col_p1:
            # Random Prompt Logic
            if 'model_prompt' not in st.session_state:
                st.session_state['model_prompt'] = "A professional fashion model, front view, neutral expression, wearing a simple white t-shirt"
            
            # Helper function to generate random prompt
            def set_random_prompt():
                try:
                    utils.configure_api(st.session_state.get('api_key_input', ''))
                    # Use a lightweight model for prompt gen if possible, or just the selected one
                    new_p = utils.generate_random_prompt()
                    st.session_state['model_prompt'] = new_p
                except Exception as e:
                    st.error(f"Generate prompt failed: {e}")

            c_prompt_label, c_prompt_btn = st.columns([3, 1])
            c_prompt_label.markdown("**角色描述 (Prompt)**")
            if c_prompt_btn.button("🎲 随机提示词", help="让 AI 生成一个随机的模特描述"):
                if not api_key:
                    st.error("需 API Key")
                else:
                    # We need to ensure API key is configured
                    utils.configure_api(api_key) 
                    with st.spinner("思考中..."):
                         new_p = utils.generate_random_prompt()
                         st.session_state['model_prompt'] = new_p
                         st.rerun()

            base_prompt = st.text_area("角色描述 (Prompt)", height=100, label_visibility="collapsed", key="model_prompt")
            
            c_opt1, c_opt2 = st.columns(2)
            auto_bg_gen = c_opt1.checkbox("自动移除背景 (白底化)", value=True, help="使用 AI 确保背景为纯白")
            # Default to TRUE for "Standard Layout"
            auto_crop_gen = c_opt2.checkbox("应用标准排版 (顶部留白400px)", value=True, help="生成后自动执行：智能裁剪头像 -> 2K画质 -> 顶部留白400px/左右100px。")
        
        with col_p2:
            pose_ref = st.file_uploader("姿势参考图 (可选)", type=["png", "jpg", "jpeg"], help="上传图片以复制姿势。")
            
        if st.button("生成模特模板", type="primary"):
            if not api_key:
                st.error("缺少 API Key")
            else:
                try:
                    utils.configure_api(api_key)
                    with st.spinner("正在生成角色..."):
                        # 1. Generate
                        pose_img = Image.open(pose_ref) if pose_ref else None
                        
                        raw_char = utils.generate_model_character(base_prompt, pose_image=pose_img, model_name=model_name)
                        
                        # 2. Auto BG Removal (Optional but recommended for consistency)
                        if auto_bg_gen:
                            with st.spinner("正在优化背景..."):
                                raw_char = utils.remove_background(raw_char, prompt="person", model_name=model_name)
                        
                        # 3. Auto Crop OR Padding
                        if auto_crop_gen:
                             with st.spinner("正在自动裁剪大头照 (Smart Crop)..."):
                                 # This handles crop + 2K upscale
                                 processed_char = utils.smart_crop_headshot(raw_char, model_name=model_name)
                        else:
                             # Old logic: Add padding
                             # Reduced padding as requested (400->200 top, 200->50 sides)
                             processed_char = utils.add_white_padding_all(raw_char, top=200, left=50, right=50, bottom=0)
                        
                        # 4. Store
                        st.session_state['current_generated_model'] = processed_char
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"错误: {e}")

    # --- Mode: Upload ---
    else: 
        st.markdown("上传一张你想用作模特的照片。")
        uploaded_model_file = st.file_uploader("上传人物图片", type=["png", "jpg", "jpeg"])
        
        if uploaded_model_file:
            input_img = Image.open(uploaded_model_file)
            st.image(input_img, caption="原始上传", width=200)
            
            # Options
            c_u1, c_u2 = st.columns(2)
            auto_bg_up = c_u1.checkbox("自动智能抠图并白底化", value=True)
            add_padding = c_u2.checkbox("添加白色留白 (上/左/右/下)", value=True)
            
            col_pad1, col_pad2, col_pad3, col_pad4 = st.columns(4)
            top_px = col_pad1.number_input("上边距 px", value=200, min_value=0, max_value=3000, step=50)
            left_px = col_pad2.number_input("左边距 px", value=50, min_value=0, max_value=3000, step=50)
            right_px = col_pad3.number_input("右边距 px", value=50, min_value=0, max_value=3000, step=50)
            bottom_px = col_pad4.number_input("下边距 px", value=0, min_value=0, max_value=3000, step=50)
            
            if st.button("处理并预览"):
                try:
                    utils.configure_api(api_key)
                    curr_img = input_img
                    
                    # 1. BG Removal
                    if auto_bg_up:
                        with st.spinner("正在去除背景..."):
                             # If API key is missing for BG removal
                            if not api_key:
                                st.error("自动抠图需要 API Key")
                                st.stop()
                            curr_img = utils.remove_background(curr_img, prompt="person", model_name=model_name)
                    
                    # 2. Padding
                    if add_padding:
                        processed_char = utils.add_white_padding_all(curr_img, top=top_px, left=left_px, right=right_px, bottom=bottom_px)
                    else:
                        processed_char = curr_img
                    
                    st.session_state['current_generated_model'] = processed_char
                    st.rerun()
                except Exception as e:
                    st.error(f"处理错误: {e}")

    # --- Preview & Save ---
    st.divider()
    if 'current_generated_model' in st.session_state:
        st.subheader("当前预览")
        col_prev1, col_prev2 = st.columns([1, 2])
        with col_prev1:
            st.image(st.session_state['current_generated_model'], caption="待保存模特 (已处理)", use_container_width=True)
            
            # --- Smart Crop Button ---
            if st.button("✂️ 智能裁剪: 仅保留大头照", help="利用 AI 自动剪裁出头部和肩膀区域，并调整为 2K 画质。"):
                try:
                    utils.configure_api(api_key)
                    with st.spinner("正在智能分析裁剪区域..."):
                        # Get current image
                        curr_prev = st.session_state['current_generated_model']
                        
                        # Apply Smart Crop
                        cropped_headshot = utils.smart_crop_headshot(curr_prev, model_name=model_name)
                        
                        # Update Session
                        st.session_state['current_generated_model'] = cropped_headshot
                        st.success("裁剪完成！已自动设为 2K 分辨率。")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"裁剪失败: {e}")
                    
        with col_prev2:
            # Initialize default name only if needed
            if 'default_model_name' not in st.session_state:
                 st.session_state['default_model_name'] = f"model_{int(datetime.datetime.now().timestamp())}"
            
            # Binding to key automatically handles persistence
            save_name = st.text_input("模特名称", value=st.session_state['default_model_name'], key="model_name_input")
            
            if st.button("保存到模特库"):
                # Use the value from the widget (key)
                final_name = st.session_state.model_name_input
                if not final_name:
                    final_name = st.session_state['default_model_name']
                    
                path = os.path.join("models", f"{final_name}.png")
                st.session_state['current_generated_model'].save(path)
                st.success(f"已保存至 {path}!")
                
                # Reset default for next time
                del st.session_state['default_model_name']
                # Optional: Clear current model to reset workflow? 
                # Or just let user continue.
                # To force a fresh name next time, we simply delete the key from session state IF we were navigating away,
                # but here we might stay.
                # Let's just update the default name to a new timestamp to indicate "Done" or ready for next?
                st.session_state['default_model_name'] = f"model_{int(datetime.datetime.now().timestamp())}"
                
                st.rerun()

    # --- Model Library ---
    st.divider()
    st.subheader("📚 我的模特库")
    
    lib_files = [f for f in os.listdir("models") if f.endswith((".png", ".jpg", ".jpeg"))]
    if not lib_files:
        st.info("库中暂无模特。请在上方生成或上传。")
    else:
        # Sort by creation time (newest first)
        lib_files.sort(key=lambda x: os.path.getmtime(os.path.join("models", x)), reverse=True)
        
        # Grid Display
        cols = st.columns(4)
        for i, f_name in enumerate(lib_files):
            f_path = os.path.join("models", f_name)
            with cols[i % 4]:
                st.image(f_path, caption=f_name, use_container_width=True)
                # Delete Button
                if st.button(f"删除###{f_name}", key=f"del_{f_name}"):
                    try:
                        os.remove(f_path)
                        st.toast(f"已删除 {f_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")


# --- TAB 2: Hat Studio ---
with tab2:
    st.header("第二步: 草帽佩戴工坊")
    
    # 1. Select Model
    model_files = [f for f in os.listdir("models") if f.endswith((".png", ".jpg"))]
    if not model_files:
        st.warning("没有找到模特图片。请先在第一步中创建并保存模特。")
        st.stop()
        
    selected_model_name = st.selectbox("选择底图模特", model_files)
    model_path = os.path.join("models", selected_model_name)
    
    # Preview selected model
    with st.expander(f"预览模特: {selected_model_name}", expanded=True):
        st.image(model_path, width=300)
    
    # 2. Upload Hat
    uploaded_hat = st.file_uploader("上传草帽图片 (透明 PNG)", type=["png"])
    
    if uploaded_hat:
        # Controls
        c1, c2, c3 = st.columns(3)
        off_x = c1.number_input("水平偏移 (Offset X)", value=0, min_value=-500, max_value=500, step=10)
        off_y = c2.number_input("垂直偏移 (Offset Y)", value=0, min_value=0, max_value=800, step=10)
        scale = c3.slider("缩放草帽", 0.5, 2.0, 1.0, 0.1)
        
        with st.expander("将草帽居中到白底正方形"):
            side_px = st.number_input("正方形边长(px)", value=1024, min_value=256, max_value=4096, step=128)
            margin_ratio = st.slider("四周留白比例", 0.05, 0.40, 0.15, 0.01)
            if st.button("生成白底方图", key="pack_hat_square"):
                try:
                    hat_img_rgba = Image.open(uploaded_hat).convert("RGBA")
                    packed = utils.place_on_white_square(hat_img_rgba, side=side_px, margin_ratio=margin_ratio)
                    st.image(packed, caption="白底正方形居中结果", use_container_width=True)
                    import io
                    buf = io.BytesIO()
                    packed.save(buf, format="PNG")
                    st.download_button("下载PNG", data=buf.getvalue(), file_name=f"hat_square_{side_px}.png", mime="image/png")
                except Exception as e:
                    st.error(f"处理失败: {e}")
        
        # Live Preview
        try:
            composite, mask = utils.process_hat_on_model(
                model_path, 
                uploaded_hat, 
                offset_x=off_x, 
                offset_y=off_y, 
                hat_scale=scale
            )
            
            st.image(composite, caption="预览 (草帽位置)", width=400)
            
            with st.expander("显示生成的遮罩 (Mask)"):
                st.image(mask, caption="遮罩 (黑色区域为保护的草帽)", width=400)
                
            hat_prompt = st.text_area("重绘提示词 (Inpainting Prompt)", "A realistic photo of person wearing this hat, perfect lighting", height=80)
            
            # --- Advanced: Hat Enhancement ---
            with st.expander("✨ 高级: 草帽细节增强"):
                st.markdown("上传多张草帽的细节图或多角度图，以增强清晰度和细节。")
                enhance_refs = st.file_uploader("参考细节图", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                enable_enhance = st.checkbox("启用细节增强 (重绘草帽区域)", value=False)
            
            if st.button("生成佩戴效果", type="primary"):
                 if not api_key:
                    st.error("缺少 API Key")
                 else:
                    try:
                        utils.configure_api(api_key)
                        with st.spinner("处理步骤 1: 佩戴草帽..."):
                            # Pass 1: Wear Hat (Protect Hat, Edit Person)
                            
                            # Standard composite flow
                            base_rgb = composite.convert("RGB")
                            
                            result_pass_1 = utils.edit_image_with_mask(
                                base_image=base_rgb,
                                mask_image=mask,
                                prompt=hat_prompt,
                                model_name=model_name
                            )
                            
                        final_result = result_pass_1
                        
                        # Pass 2: Enhancement (Protect Person, Edit Hat)
                        if enable_enhance and enhance_refs:
                            with st.spinner("处理步骤 2: 增强草帽细节..."):
                                # 1. Analyze Details
                                ref_imgs = [Image.open(f) for f in enhance_refs]
                                detail_desc = utils.analyze_hat_details(ref_imgs)
                                st.success(f"已分析细节: {detail_desc[:100]}...")
                                
                                # 2. Invert Mask (Black=Person(Protected), White=Hat(Edit))
                                # Original mask: Black=Hat, White=Background
                                # We want to Edit Hat -> White
                                # Protect Background -> Black
                                # So: Invert
                                from PIL import ImageOps
                                enhance_mask = ImageOps.invert(mask)
                                
                                # 3. Enhance Prompt
                                enhance_prompt = f"High definition closeup of {detail_desc}. {hat_prompt}"
                                
                                # 4. Generate
                                result_pass_2 = utils.edit_image_with_mask(
                                    base_image=result_pass_1, # Use result of pass 1
                                    mask_image=enhance_mask,
                                    prompt=enhance_prompt,
                                    model_name=model_name
                                )
                                final_result = result_pass_2
                                st.caption("已应用细节增强")

                        st.image(final_result, caption="最终结果", use_container_width=True)
                            
                    except Exception as e:
                        st.error(f"错误: {e}")
                        
        except Exception as e:
            st.error(f"处理错误: {e}")


# --- TAB 7: Shadow Lightener ---
with tab7:
    st.header("💡 光影调整 (Shadow Reform)")
    st.markdown("手动涂抹图片中的阴影区域，AI 将自动把阴影变淡，使光照更自然。")
    
    shadow_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], key="shadow_input")
    
    if shadow_file:
        # Load and resize for canvas (canvas has fixed width issues usually, but we can set it)
        raw_img = Image.open(shadow_file).convert("RGB")
        
        # Resize for display/canvas if too big (limit to 800px width for UI mainly)
        # But we need to map validity back to original. 
        # For simplicity, let's keep it reasonable or canvas handles it.
        # st_canvas uses pixels.
        
        # Display Canvas
        st.subheader("涂抹阴影区域")
        
        # Canvas parameters
        col_s1, col_s2 = st.columns([1, 1])
        with col_s1:
             stroke_width = st.slider("笔刷大小", 1, 50, 20)
             # Add local model selector
             shadow_model = st.selectbox("修复模型", ["gemini-2.0-flash-exp", "gemini-3-pro-image-preview", "gemini-3-pro-image"], index=0, help="尝试不同模型可能有不同效果")
        with col_s2:
             shadow_intensity = st.select_slider("去影强度", options=["Soft", "Strong"], value="Strong") # Default to Strong now
        
        # Create a canvas component
        
        # Calculate canvas dimensions to match image aspect ratio, but max width ~700
        disp_width = 700
        if raw_img.width > disp_width:
             ratio = disp_width / raw_img.width
             disp_height = int(raw_img.height * ratio)
             disp_width = 700 # fix exact
        else:
             disp_width = raw_img.width
             disp_height = raw_img.height
             
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
            stroke_width=stroke_width,
            stroke_color="rgba(255, 255, 255, 1.0)", # White stroke for mask
            background_image=raw_img if raw_img else None,
            update_streamlit=True,
            height=disp_height,
            width=disp_width,
            drawing_mode="freedraw",
            key="shadow_canvas",
        )
        
        if st.button("开始去影", type="primary"):
            if canvas_result.image_data is not None:
                # Get the mask
                # canvas_result.image_data is a numpy array (H, W, 4)
                # We need to convert it to a PIL Image (L mode) and Resize back to original raw_img size
                
                import numpy as np
                mask_data = canvas_result.image_data
                
                # Extract Alpha channel as mask (or just check non-zero pixels)
                # The drawn stroke is white (255,255,255,255) in our config above? 
                # Actually st_canvas returns the stroke layer.
                
                mask_np = mask_data[:, :, 3] # Alpha channel
                mask_pil = Image.fromarray(mask_np.astype('uint8'), mode='L')
                
                # Resize mask back to original image size
                if mask_pil.size != raw_img.size:
                    mask_pil = mask_pil.resize(raw_img.size, Image.Resampling.NEAREST)
                    
                # Check if empty (sometimes user clicks without drawing)
                # Using getbbox() is safest check for non-black images
                if mask_pil.getbbox() is None:
                    st.warning("请先在图片上涂抹要处理的阴影区域！")
                elif not api_key:
                    st.error("缺少 API Key")
                else:
                    try:
                        utils.configure_api(api_key)
                        with st.spinner("正在柔化阴影 (Retouching)..."):
                            # Call utils
                            res = utils.reduce_shadows(raw_img, mask_pil, intensity=shadow_intensity, model_name=shadow_model)
                            
                        st.success("处理完成！")
                        
                        # Show Comparison
                        c1, c2 = st.columns(2)
                        with c1:
                            st.image(raw_img, caption="原图", use_container_width=True)
                        with c2:
                            st.image(res, caption="去影结果", use_container_width=True)
                        
                        # Download
                        import io
                        buf = io.BytesIO()
                        res.save(buf, format="PNG")
                        st.download_button("下载结果 (PNG)", buf.getvalue(), "shadow_fix.png", "image/png")
                        
                    except Exception as e:
                        st.error(f"处理失败: {e}")
            else:
                st.warning("请先涂抹区域。")

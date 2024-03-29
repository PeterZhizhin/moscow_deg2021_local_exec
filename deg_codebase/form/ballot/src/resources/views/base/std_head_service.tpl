{if $mosDesign} 
	{include file="$base_template_path/std_mos/std_head_service.tpl"}
{else}

{assign var=faq value={$faq} scope="global"}
{assign var=has_additional_legals value={$has_additional_legals} scope="global"}
{assign var=download_app_file_enabled value={$download_app_file_enabled} scope="global"}

{if $has_additional_legals} 
	{if count($availableDeclarants) == 1}
		{include file="$base_template_path/std_blocks/std_select_legal.tpl"}
	{else}
	<div class="legal_select">
		{include file="$base_template_path/std_blocks/std_select_legal.tpl"}
	</div>
	{/if}
{/if}
{nocache}
{if $upload_config}
{if $use_external_storage}

	{if !$custom_docs}
		<script type="text/javascript" src="{$CFG_JS_HOST}/common/js_v3/forms/mpgu.ext.docs.js"></script>
	{/if}
	{if (isset($ched_url))}
		<script type="text/javascript" src="{$ched_url}"></script>
	{/if}


<script type="text/javascript" src="{$CFG_JS_HOST}/common/js_v3/forms/mpgu.uploader.js?ched_version={$ched_version}"></script>
{else}<script type="text/javascript" src="{$CFG_JS_HOST}/common/js_v3/forms/mpgu.uploader.js"></script>
{/if}
<script type="text/javascript">


	UploadController.init({
		org_id: '{$org_id}',
		form_id: '{$form_id}',
		limits: {$upload_config},
		upload_hash: '{$upload_hash}',
		use_external_storage: {$use_external_storage}
	});
</script>
{/if}
{/nocache}

<script type="text/javascript">
	var person_type = '{$person_type}';

	{if !empty($moscowDistrictsJs_form_json)}
		if (typeof (manual_rayons)=='undefined'||manual_rayons==Array)
			var manual_rayons = {if $moscowDistrictsJs_form_json}{$moscowDistrictsJs_form_json}{else}[]{/if}; 
	{/if}

	{if !empty($BTI_district_and_areas_form_json)}
		if (typeof (BTI_district_and_areas_form)=='undefined'||BTI_district_and_areas_form==Array)
			var BTI_district_and_areas_form = {if $BTI_district_and_areas_form_json}{$BTI_district_and_areas_form_json}{else}[]{/if};
	{/if}

	if (MPGU!=undefined) {
		MPGU.FORM = {if isset($showParams)}{$showParams}{else}{ }{/if};
		MPGU.controller={if isset($controllerParams)}{$controllerParams}{else}{ }{/if};
	}
	else console.error('Файл конфига не прогружен');

</script>

{if $video}
<script type="text/javascript">
	function viewShield(width, height){
		messagebox('Интерактивная инструкция', $('#instruction_video_block').html(), width);
		$('.popup_messagebox').css({ 'position':'fixed', 'top':'100px' });
		$('.popup_messagebox #instruction_video_container > video').attr('autoplay','autoplay');
	};
	$(document).on('click.video','.form-video a',function(){
		viewShield(1024,576);
		return false; 
	});
	</script>
	{assign var=exploded value='.'|explode:$video}
	{assign var=videoFormat value=$exploded|@end} 

	<div id="instruction_video_block" class='hidden'>
		<div id="instruction_video_container">
			<video controls>
				<source src="{$video}" type="video/{$videoFormat}">
				<p>К сожалению, Ваш браузер не поддерживает HTML5. Просьба, обновить браузер и попробовать снова.</p>
			</video>
		</div>
	</div>

{/if}
{if $form_message}
	{if $form_message_type == 1}
		{assign var=form_infoblock_color value="red"}
	{else}
		{if $form_message_type == 2}
			{assign var=form_infoblock_color value="orange"}
		{else}
			{assign var=form_infoblock_color value="white"}
		{/if}
	{/if}
	{include file="$base_template_path/std_blocks/std_infoblock.tpl" color=$form_infoblock_color text={$form_message}}
{/if}
<div id="form-detail-info" style="display:none;">
		<div class="form-manual-container">


				<h2>Инструкция по оформлению услуги
						{include file="$base_template_path/std_blocks/std_print_link.tpl" print_block=".popup_messagebox" onclick="FormController.print($(this));"}
						<!--a href="#" onclick="print_instruction(); return false" class="print_button"><img src="/common/img/elem/print_icon.png" alt="" /></a-->
				</h2>

				{if isset($manual_info)}
						<p>{$manual_info}</p>
				{/if}
				<h3 style="padding-top:0px;">
				{if $video}
					<div class="form-video">
						<a href="#" class="dashed-link" title="Открыть видеоинструкцию по использованию электронной услуги">Посмотреть интерактивную инструкцию</a>
					</div>
				{/if}
				{if $manual_file}
						<div class="form-manual-file">
							<a href="{$manual_file}" class="dashed-link" target="_blank" title="Открыть инструкцию по использованию электронной услуги">Скачать инструкцию</a>
						</div>
				{/if}

				{assign var="manual_file" value="`$cur_template_path`/manualTxt.tpl"}
				{if file_exists($manual_file)}
						<div class="form-manual">
								{include file="$manual_file"}
						</div>
				{/if}
					</h3>
		</div>
</div>

<div class="row body-container">
	<div class="col-xs-12 col-sm-9 col-lg-9" id="form-base">
		<ul id="form-steps-container" class="nav nav-tabs"></ul>					
		{if $description}
			<div>{mpgu_button href="$description" target='_blank' title='Перейти на карточку с описанием услуги' text='Описание услуги'}</div>
		{/if}
		{if $print_and_download}
			<div style="float:right;">
				<a title="Распечатать информацию по выбранному шагу" {if $print_and_download_iswork}onclick="print_page(); return false;"{else}onclick="alert_instruction(); return false;"{/if} class="print_style"><span class="print_style">Распечатать</span></a>
				<a title="Скачать информацию по выбранному шагу" {if $print_and_download_iswork}onclick="save_page(); return false;"{else}onclick="alert_instruction(); return false;"{/if} class="download_style"><span class="download_style">Скачать</span></a>
			</div>
			<br/>
			<div class="line_greey" style="height: 0"></div>
		{/if}

		{assign var=show_right_footer_block value="true"}


	{if $use_pep}
		{*добавил блок простой электронной подписи, если статус подходящий*}
		{include file="$base_template_path/std_blocks/std_pep.tpl" }

	{/if}

{/if}
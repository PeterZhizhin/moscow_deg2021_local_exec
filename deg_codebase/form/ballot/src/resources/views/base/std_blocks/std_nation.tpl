{array vars="array(
'аварец' => 'аварец',
'азербайджанец' => 'азербайджанец',
'армянин' => 'армянин',
'афганец' => 'афганец',
'башкир' => 'башкир',
'белорус' => 'белорус',
'болгарин' => 'болгарин',
'великорос' => 'великорос',
'венгр' => 'венгр',
'вьетнамец' => 'вьетнамец',
'гагауз' => 'гагауз',
'гагаус' => 'гагаус',
'грек' => 'грек',
'грузин' => 'грузин',
'даргинец' => 'даргинец',
'еврей' => 'еврей',
'кабардинец' => 'кабардинец',
'казах' => 'казах',
'карачаевец' => 'карачаевец',
'карел' => 'карел',
'киргиз' => 'киргиз',
'китаец' => 'китаец',
'коми' => 'коми',
'коми-пермяк' => 'коми-пермяк',
'кореец' => 'кореец',
'кыргыз' => 'кыргыз',
'латыш' => 'латыш',
'лезгин' => 'лезгин',
'литовец' => 'литовец',
'магометанин' => 'магометанин',
'мари' => 'мари',
'мариец' => 'мариец',
'молдованин' => 'молдованин',
'мордвин' => 'мордвин',
'немец' => 'немец',
'осетин' => 'осетин',
'пермяк' => 'пермяк',
'поляк' => 'поляк',
'румын' => 'румын',
'русский' => 'русский',
'табасаранец' => 'табасаранец',
'таджик' => 'таджик',
'татарин' => 'татарин',
'туркмен' => 'туркмен',
'удмурт' => 'удмурт',
'узбек' => 'узбек',
'украинец' => 'украинец',
'финн' => 'финн',
'цыган' => 'цыган',
'черкес' => 'черкес',
'чеченец' => 'чеченец',
'чуваш' => 'чуваш',
'эстонец' => 'эстонец',
'якут' => 'якут',
'иное' => 'иное'
)" assign="nation_list_male"}

{array vars="array(
'абазинка' => 'абазинка',
'азербайджанка' => 'азербайджанка',
'армянка' => 'армянка',
'башкирка' => 'башкирка',
'белоруска' => 'белоруска',
'болгарка' => 'болгарка',
'венгерка' => 'венгерка',
'вьетнамка' => 'вьетнамка',
'грузинка' => 'грузинка',
'еврейка' => 'еврейка',
'ингушка' => 'ингушка',
'иранка' => 'иранка',
'казашка' => 'казашка',
'калмычка' => 'калмычка',
'карелка' => 'карелка',
'коми' => 'коми',
'коми-пермячка' => 'коми-пермячка',
'кореянка' => 'кореянка',
'кыргызка' => 'кыргызка',
'латышка' => 'латышка',
'лачка' => 'лачка',
'лезгинка' => 'лезгинка',
'литовка' => 'литовка',
'магометанка' => 'магометанка',
'мари' => 'мари',
'марийка' => 'марийка',
'молдованка' => 'молдованка',
'мордвинка' => 'мордвинка',
'мордовка' => 'мордовка',
'немка' => 'немка',
'осетинка' => 'осетинка',
'полька' => 'полька',
'русская' => 'русская',
'таджичка' => 'таджичка',
'татарка' => 'татарка',
'туркменка' => 'туркменка',
'удмуртка' => 'удмуртка',
'узбечка' => 'узбечка',
'украинка' => 'украинка',
'финка' => 'финка',
'цыганка' => 'цыганка',
'чеченка' => 'чеченка',
'чувашка' => 'чувашка',
'эвенка' => 'эвенка',
'эстонка' => 'эстонка',
'якутка' => 'якутка',
'иное' => 'иное'
)" assign="nation_list_female"}

{include file="$base_template_path/std_blocks/std_select.tpl" items=$nation_list_male   label=$label required=$required context_search=$context_search name="field[{$name_1}]"   container_class="{$container_class} {if isset($value)&&value!='1'}hidden{/if}"   id="{$id}_1"}
{include file="$base_template_path/std_blocks/std_select.tpl" items=$nation_list_female label=$label required=$required context_search=$context_search name="field[{$name_2}]" container_class="{$container_class} {if !isset($value)||isset($value)&&value!='2'}hidden{/if}" id="{$id}_2"}


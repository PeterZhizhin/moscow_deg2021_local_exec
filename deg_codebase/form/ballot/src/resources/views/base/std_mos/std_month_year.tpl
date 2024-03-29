{assign var=month_year_id value=$id|default:''}
{assign var=container_class value=$container_class|default:'payment-period'}
{assign var=thisyear value=$smarty.now|date_format:"%Y"}
{assign var=thismonth value=$smarty.now|date_format:"%m"}
{array vars="array('$thisyear' => '$thisyear')" assign="years_default"}
{if (!isset($month_name)||(isset($month_name)&&!$month_name))&&isset($name)&&$name}{$month_name = "$name[month]"}{/if}
{if (!isset($year_name)||(isset($year_name)&&!$year_name))&&isset($name)&&$name}{$year_name = "$name[year]"}{/if}
{array vars="array('1' => 'Январь','2' => 'Февраль','3' => 'Март','4' => 'Апрель','5' => 'Май','6' => 'Июнь','7' => 'Июль','8' => 'Август','9' => 'Сентябрь','10' => 'Октябрь','11' => 'Ноябрь','12' => 'Декабрь',)" assign="months_default"}
{assign var=month_items value=$month_items|default:$months_default}
{assign var=month_name value=$month_name|default:'month'}
{assign var=month_value value=$month_value|default:$thismonth}
{assign var=month_no_empty value=$month_no_empty|default:'true'}

{assign var=year_items value=$year_items|default:$years_default}
{assign var=year_name value=$year_name|default:'year'}
{assign var=year_value value=$value|default:$thisyear}

	    
   <div class="field--is--date field field--lg field--has-clear field--error-popup field--filled element-control element-control-show-label form-horizoontal chosen-block wrap {if $container_class}{$container_class}{/if}">
	<div class="field__inner">     
                <select class="master-field chosen{if isset($month_class)} {$month_class}{/if}" id="month{$month_year_id}" name="{if isset($month_name)}{$month_name}{/if}"data-error-message="{if isset($month_error_message)}{$month_error_message}{else}Поле заполнено некорректно{/if}"{if isset($required) && $required} required="required"{/if}>
                {if isset($month_items)}
                    {foreach from=$month_items item=item_name key=item_key}

                            {if $item_key == $month_value}
                                    <option value="{$item_key}" selected>{$item_name}</option>
                            {else}
                                    <option value="{$item_key}">{$item_name}</option>
                            {/if}
                    {/foreach}
                {/if}
		</select>
             
		<label class="control-label field__label   element-label">
			<span class="field__label-inner">Месяц{if isset($required) && $required} <span class="required"></span>{/if}</span>
		</label>
                <div class="field__clear">
		</div>
		
		      
        </div>        
    </div>
    <div class="field--is--date field field--lg field--has-clear field--error-popup field--filled element-control element-control-show-label form-horizoontal chosen-block wrap {if $container_class}{$container_class}{/if}">
	<div class="field__inner">     
                <select  class="master-field chosen{if isset($year_class)} {$year_class}{/if}" id="year{$month_year_id}"  name="{if isset($year_name)}{$year_name}{/if}"data-error-message="{if isset($year_error_message)}{$year_error_message}{else}Поле заполнено некорректно{/if}"{if isset($required) && $required} required="required"{/if}>
                {if isset($year_items)}
                {foreach from=$year_items item=item_name key=item_key}
                        {if $item_key == $year_value}
                                <option value="{$item_key}" selected>{$item_name}</option>
                        {else}
                                <option value="{$item_key}">{$item_name}</option>
                        {/if}
                {/foreach}
                {/if}
		</select>
             
		<label class="control-label field__label   element-label">
			<span class="field__label-inner">Год{if isset($required) && $required} <span class="required"></span>{/if}</span>
		</label>
                <div class="field__clear">
		</div>
		  
        </div>        
    </div> 


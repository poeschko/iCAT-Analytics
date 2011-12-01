USE ictm3;

set @instance = "ictm2011-11-30_04h02m";
SET character_set_database=utf8;
SET FOREIGN_KEY_CHECKS = 0;

load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_annotation.txt' replace into table icd_annotation
	(@name, type, @author_id, created, modified, @annotates_id, subject, body, context, related, archived, browser_text)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	author_id=concat(@instance, @author_id), annotates_id=concat(@instance, @annotates_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_category.txt' replace into table icd_category
	(name, display, sorting_label, definition, display_status, primary_tag, secondary_tag)
	set instance_name=concat(@instance, name), instance=@instance;
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_category_title_language.txt' replace into table icd_categorytitles
	(@category, @title, @lang)
	set category_id=concat(@instance, @category), title=concat(@title), language_code=@lang;
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_category_definition_language.txt' replace into table icd_categorydefinitions
	(@category, @definition, @lang)
	set category_id=concat(@instance, @category), definition=concat(@definition), language_code=@lang;
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_category_children.txt' replace into table icd_category_children
	(@from_category_id, @to_category_id)
	set from_category_id=concat(@instance, @from_category_id), to_category_id=concat(@instance, @to_category_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_change.txt' replace into table icd_change
	(@name, type, @author_id, timestamp, @apply_to_id, @composite_id, context, action, browser_text)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	author_id=concat(@instance, @author_id), apply_to_id=concat(@instance, @apply_to_id), composite_id=concat(@instance, @composite_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_linearizationspec.txt' replace into table icd_linearizationspec
	(linearization, @parent_id, @child_id, label, is_included)
	set instance=@instance, parent_id=concat(@instance, @parent_id), child_id=concat(@instance, @child_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_ontologycomponent.txt' replace into table icd_ontologycomponent
	(@name, type, @category_id)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	category_id=concat(@instance, @category_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_user.txt' replace into table icd_user
	(type, name)
	set instance_name=concat(@instance, name), instance=@instance;
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_user_domain_of_interest.txt' replace into table icd_user_domain_of_interest
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_user_watched_branches.txt' replace into table icd_user_watched_branches
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);
load data local infile 'C:\\Users\\simon\\Desktop\\Github\\iCAT-Analytics\\export\\src\\ICTM-Exports\\ictm2011-11-30_04h02m\\ictm_user_watched_entities.txt' replace into table icd_user_watched_entities
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);


delete from icd_annotatablething where instance = @instance;

insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, substr(annotatablething_ptr_id, length(@instance)+1)
	from icd_annotation where _instance = @instance;
insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, substr(annotatablething_ptr_id, length(@instance)+1)
	from icd_change where _instance = @instance;
insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, substr(annotatablething_ptr_id, length(@instance)+1)
	from icd_ontologycomponent where _instance = @instance;

/*insert into icd_annotatablething (name) select annotatablething_ptr_id from icd_change;
insert into icd_annotatablething (name) select annotatablething_ptr_id from icd_ontologycomponent;*/

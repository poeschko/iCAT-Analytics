set @instance = "2010-06-01_04h02m";

load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_annotation.txt' replace into table icd_annotation
	(@name, type, @author_id, created, modified, @annotates_id, subject, body, context, related, archived, browser_text)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	author_id=concat(@instance, @author_id), annotates_id=concat(@instance, @annotates_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_category.txt' replace into table icd_category
	(name, display, sorting_label, definition, display_status, primary_tag, secondary_tag)
	set instance_name=concat(@instance, name), instance=@instance;
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_category_children.txt' replace into table icd_category_children
	(@from_category_id, @to_category_id)
	set from_category_id=concat(@instance, @from_category_id), to_category_id=concat(@instance, @to_category_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_change.txt' replace into table icd_change
	(@name, type, @author_id, timestamp, @apply_to_id, @composite_id, context, action, browser_text)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	author_id=concat(@instance, @author_id), apply_to_id=concat(@instance, @apply_to_id), composite_id=concat(@instance, @composite_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_linearizationspec.txt' replace into table icd_linearizationspec
	(linearization, @parent_id, @child_id, label, is_included)
	set instance=@instance, parent_id=concat(@instance, @parent_id), child_id=concat(@instance, @child_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_ontologycomponent.txt' replace into table icd_ontologycomponent
	(@name, type, @category_id)
	set annotatablething_ptr_id=concat(@instance, @name), _instance=@instance, _name=@name,
	category_id=concat(@instance, @category_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_user.txt' replace into table icd_user
	(type, name)
	set instance_name=concat(@instance, name), instance=@instance;
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_user_domain_of_interest.txt' replace into table icd_user_domain_of_interest
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_user_watched_branches.txt' replace into table icd_user_watched_branches
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);
load data local infile '/Users/Jan/Uni/Stanford/ICD/data/icd_user_watched_entities.txt' replace into table icd_user_watched_entities
	(@user_id, @ontologycomponent_id)
	set user_id=concat(@instance, @user_id), ontologycomponent_id=concat(@instance, @ontologycomponent_id);

-- delete from icd_annotatablething where instance = @instance;
	
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

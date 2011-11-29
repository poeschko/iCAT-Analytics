set @instance = "nci100400";

load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_category.txt' replace into table icd_category
	(name, display, sorting_label, definition, display_status, primary_tag, secondary_tag)
	set instance_name=concat(@instance, name), instance=@instance;
	
load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_category_children.txt' replace into table icd_category_children
	(@from_category_id, @to_category_id)
	set from_category_id=concat(@instance, @from_category_id), to_category_id=concat(@instance, @to_category_id);

load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_change.txt' replace into table icd_change
	(@index, @name, type, @author_id, timestamp, @apply_to_id, @composite_id, context, action, browser_text)
	set _name=concat("_", @index, "_", @name), annotatablething_ptr_id=concat(@instance, _name), _instance=@instance,
	author_id=concat(@instance, @author_id), apply_to_id=concat(@instance, "_", @index, "_", @apply_to_id),
	composite_id=concat(@instance, "_", @index, "_", @composite_id);

/*load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_annotation.txt' replace into table icd_annotation
	(@index, @name, type, @author_id, created, modified, @annotates_id, subject, body, context, related, archived, browser_text)
	set annotatablething_ptr_id=concat(@instance, @index, "_", @name), _instance=@instance, _name=@name,
	author_id=concat(@instance, @author_id), annotates_id=concat(@instance, @index, "_", @annotates_id);
*/
	
load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_ontologycomponent.txt' replace into table icd_ontologycomponent
	(@index, @name, type, @category_id)
	set _name=concat("_", @index, "_", @name), annotatablething_ptr_id=concat(@instance, _name), _instance=@instance,
	category_id=concat(@instance, @category_id);
	
/*load data local infile '/Users/Jan/Uni/Stanford/ICD/data_nci/nci_user.txt' replace into table icd_user
	(type, name)
	set instance_name=concat(@instance, name), instance=@instance;*/

-- delete from icd_annotatablething where instance = @instance;
	
insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, _name
	from icd_annotation where _instance = @instance;
insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, _name
	from icd_change where _instance = @instance;
insert into icd_annotatablething (instance_name, instance, name)
	select annotatablething_ptr_id, @instance, _name
	from icd_ontologycomponent where _instance = @instance;

/*insert into icd_annotatablething (name) select annotatablething_ptr_id from icd_change;
insert into icd_annotatablething (name) select annotatablething_ptr_id from icd_ontologycomponent;*/

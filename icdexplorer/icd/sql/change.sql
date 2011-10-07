alter table icd_change
add index instance_timestamp (_instance, timestamp),
add index apply_to_action_context (apply_to_id, action(100), context(30)),
add index apply_to_author (apply_to_id, author_id),
add index apply_to_timestamp_property_author (apply_to_id, timestamp, property(100), author_id(100)),
add index apply_to_property_timestamp_author (apply_to_id, property, timestamp, author_id(100)),
add index instance_author_reverted_by (_instance, author_id, reverted_by_id),
add index instance_property (_instance, property);
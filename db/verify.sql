-- db/verify.sql - proves each fix works. Run:  psql -v ON_ERROR_STOP=1 -d <db> -f db/verify.sql
-- Everything runs inside a transaction that is rolled back; it leaves no data behind.
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    got BOOLEAN; n INT;
    cust UUID := 'e0000000-0000-4000-8000-000000000001';
    mast UUID := 'e0000000-0000-4000-8000-000000000002';
    mast2 UUID := 'e0000000-0000-4000-8000-000000000003';
    lst UUID := 'e0000000-0000-4000-8000-0000000000a1';
    off UUID := 'e0000000-0000-4000-8000-0000000000b1';
    pl INT; el INT; pt_wrong BIGINT;
BEGIN
    -- 1. the 8 core categories ------------------------------------------------------------------------------
    SELECT count(*) INTO n FROM service_categories WHERE is_active;
    ASSERT n = 8, format('expected 8 active categories, got %s', n);
    ASSERT (SELECT count(*) FROM service_categories WHERE is_active AND slug IS NOT NULL AND name_az IS NOT NULL) = 8, 'category without slug/name_az';
    ASSERT NOT (SELECT is_active FROM service_categories WHERE category_name = 'Carpentry'), 'Carpentry should be inactive';
    -- 2. taxonomy ------------------------------------------------------------------------------------------------
    ASSERT (SELECT count(*) FROM problem_types) = 56, 'expected 56 problem types';
    ASSERT (SELECT count(*) FROM skills WHERE skill_code IS NOT NULL) >= 54, 'skills missing codes';
    ASSERT NOT EXISTS (SELECT 1 FROM problem_types pt WHERE NOT EXISTS (SELECT 1 FROM problem_type_skills s WHERE s.problem_type_id = pt.problem_type_id)), 'problem type without skill';
    SELECT category_id INTO pl FROM service_categories WHERE slug = 'plumbing';
    SELECT category_id INTO el FROM service_categories WHERE slug = 'electrical';

    -- fixtures
    INSERT INTO users (user_id, full_name, phone_number, password_hash) VALUES
        (cust,  'Verify Customer', '050 000 00 11', 'x'), (mast, 'Verify Master', '+994500000022', 'x'), (mast2, 'Verify Master2', '+994500000033', 'x');
    ASSERT (SELECT phone_number FROM users WHERE user_id = cust) = '+994500000011', 'phone not normalised to E.164';
    INSERT INTO user_roles (user_id, role) VALUES (cust, 'Customer'), (mast, 'Master'), (mast2, 'Master'), (mast, 'Customer');
    INSERT INTO customer_profiles (user_id) VALUES (cust), (mast);
    INSERT INTO master_profiles (user_id) VALUES (mast), (mast2);

    -- 3. phone: four spellings of one number = one account --------------------------------------------------------
    got := FALSE;
    BEGIN INSERT INTO users (full_name, phone_number, password_hash) VALUES ('Dup', '0500000011', 'x');
    EXCEPTION WHEN unique_violation THEN got := TRUE; END;
    ASSERT got, 'duplicate phone in another format was accepted';
    got := FALSE;
    BEGIN INSERT INTO users (full_name, phone_number, password_hash) VALUES ('Bad', '12345678', 'x');
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'non E.164 phone was accepted';

    -- 4. service areas with NULL district --------------------------------------------------------------------------
    INSERT INTO master_service_areas (master_id, city, district) VALUES (mast, 'Sumqayıt', NULL);
    got := FALSE;
    BEGIN INSERT INTO master_service_areas (master_id, city, district) VALUES (mast, 'Sumqayıt', NULL);
    EXCEPTION WHEN unique_violation THEN got := TRUE; END;
    ASSERT got, 'duplicate NULL-district service area was accepted';

    -- 5. listing <-> problem type consistency (composite FK) ------------------------------------------------------
    INSERT INTO listings (listing_id, customer_id, category_id, problem_type_id, title, description, city, district, full_address)
    VALUES (lst, cust, pl, (SELECT problem_type_id FROM problem_types WHERE code = 'faucet_leak'), 'Faucet leak test', 'Faucet leaks under the sink', 'Bakı', 'Nəsimi', 'secret address 1');
    SELECT problem_type_id INTO pt_wrong FROM problem_types WHERE code = 'socket_not_working';
    got := FALSE;
    BEGIN UPDATE listings SET problem_type_id = pt_wrong WHERE listing_id = lst;   -- electrical problem on a plumbing listing
    EXCEPTION WHEN foreign_key_violation THEN got := TRUE; END;
    ASSERT got, 'problem type from another category was accepted';

    -- 6. offers ---------------------------------------------------------------------------------------------------
    got := FALSE;
    BEGIN INSERT INTO master_offers (listing_id, master_id, message, proposed_total, labor_cost, materials_cost, travel_cost, other_cost, estimated_duration_value, estimated_duration_unit)
          VALUES (lst, mast2, 'total does not match parts', 5, 40, 20, 5, 0, 1, 'Hours');
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'offer total != sum of parts was accepted';
    got := FALSE;
    BEGIN INSERT INTO listings (customer_id, category_id, title, description, city, district, full_address) VALUES (mast, pl, 'Own listing', 'Master own listing', 'Bakı', 'Nəsimi', 'x');
          INSERT INTO master_offers (listing_id, master_id, message, proposed_total, estimated_duration_value, estimated_duration_unit)
          SELECT listing_id, mast, 'offer on my own listing', 10, 1, 'Hours' FROM listings WHERE customer_id = mast;
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'self-offer was accepted';
    INSERT INTO master_offers (offer_id, listing_id, master_id, message, proposed_total, labor_cost, materials_cost, travel_cost, other_cost, estimated_duration_value, estimated_duration_unit)
    VALUES (off, lst, mast2, 'valid offer', 65, 40, 20, 5, 0, 2, 'Hours');

    -- 7. jobs / reviews ---------------------------------------------------------------------------------------------
    got := FALSE;
    BEGIN INSERT INTO jobs (listing_id, offer_id, customer_id, master_id, agreed_price) VALUES (lst, off, mast2, mast2, 65);
    EXCEPTION WHEN check_violation OR foreign_key_violation THEN got := TRUE; END;
    ASSERT got, 'job with customer = master was accepted';
    INSERT INTO jobs (job_id, listing_id, offer_id, customer_id, master_id, agreed_price, status)
    VALUES ('e0000000-0000-4000-8000-0000000000c1', lst, off, cust, mast2, 65, 'Agreed');
    got := FALSE;
    BEGIN INSERT INTO reviews (job_id, customer_id, master_id, rating) VALUES ('e0000000-0000-4000-8000-0000000000c1', cust, mast2, 5);
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'review on a non-completed job was accepted';
    UPDATE jobs SET status = 'Completed' WHERE job_id = 'e0000000-0000-4000-8000-0000000000c1';
    INSERT INTO reviews (job_id, customer_id, master_id, rating) VALUES ('e0000000-0000-4000-8000-0000000000c1', cust, mast2, 5);   -- now allowed

    -- 8. profiles need their role (deferred; force the check now) ------------------------------------------------------
    INSERT INTO users (user_id, full_name, phone_number, password_hash) VALUES ('e0000000-0000-4000-8000-0000000000d1', 'No Role', '+994500000044', 'x');
    got := FALSE;
    BEGIN INSERT INTO master_profiles (user_id) VALUES ('e0000000-0000-4000-8000-0000000000d1');
          SET CONSTRAINTS trg_master_profile_requires_role IMMEDIATE;
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'master profile without Master role was accepted';

    -- 9. ML storage for photo predictions -----------------------------------------------------------------------------
    INSERT INTO ml_predictions (task_name, entity_type, entity_id, model_name, model_version, prediction)
    VALUES ('damage_detect', 'Attachment', gen_random_uuid(), 'yolo', '0', '{}');

    -- 10. training view: private by default, PII-free when consent is given ----------------------------------------------
    ASSERT (SELECT count(*) FROM ml_training_listings WHERE listing_id = lst) = 0, 'listing visible to ML without consent';
    UPDATE customer_profiles SET ml_training_consent = TRUE, ml_training_consent_at = now() WHERE user_id = cust;
    ASSERT (SELECT count(*) FROM ml_training_listings WHERE listing_id = lst) = 0, 'DRAFT listing visible to ML';
    UPDATE listings SET status = 'Published', published_at = now(), expires_at = now() + INTERVAL '3 days' WHERE listing_id = lst;
    ASSERT (SELECT count(*) FROM ml_training_listings WHERE listing_id = lst) = 1, 'consented, published listing missing from ML view';
    ASSERT (SELECT problem_type_code FROM ml_training_listings WHERE listing_id = lst) = 'faucet_leak', 'problem type missing in ML view';
    ASSERT NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ml_training_listings'
                       AND column_name IN ('full_address', 'latitude', 'longitude', 'full_name', 'phone_number', 'email', 'customer_id')), 'PII column in ML view';
    got := FALSE;
    BEGIN UPDATE customer_profiles SET ml_training_consent = TRUE, ml_training_consent_at = NULL WHERE user_id = mast;
    EXCEPTION WHEN check_violation THEN got := TRUE; END;
    ASSERT got, 'consent without timestamp was accepted';

    RAISE NOTICE 'ALL 22 ASSERTIONS PASSED';
END $$;
ROLLBACK;

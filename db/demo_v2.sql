-- DEMO DATA ONLY. Do not use the placeholder password hashes in production.
-- Generate real Argon2id/bcrypt hashes inside the Node.js authentication service.
-- Run order: db/migrations/001_initial_schema.sql, 002_ml_ready_fixes.sql, db/seed_taxonomy.sql, then this file.
-- All people, e-mails and phone numbers below are FICTIONAL.
-- v2: repeatable (fixed ids + ON CONFLICT), dates relative to today, listing carries a confirmed problem_type.

BEGIN;

INSERT INTO users (user_id, full_name, phone_number, email, password_hash, phone_verified, email_verified)
VALUES
('11111111-1111-4111-8111-111111111111', 'Aysel Məmmədova', '+994500000001', 'aysel@example.com', 'REPLACE_WITH_ARGON2ID_HASH_FROM_NODEJS', TRUE, TRUE),
('22222222-2222-4222-8222-222222222222', 'Elvin Əliyev', '+994500000002', 'elvin@example.com', 'REPLACE_WITH_ARGON2ID_HASH_FROM_NODEJS', TRUE, TRUE)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_roles (user_id, role)
VALUES
('11111111-1111-4111-8111-111111111111', 'Customer'),
('22222222-2222-4222-8222-222222222222', 'Master')
ON CONFLICT (user_id, role) DO NOTHING;

INSERT INTO customer_profiles (user_id, preferred_contact_method)
VALUES ('11111111-1111-4111-8111-111111111111', 'Platform_Message')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO master_profiles (
    user_id, business_name, bio, years_experience, verification_status,
    profile_score, is_available, accepts_emergency_jobs
)
VALUES (
    '22222222-2222-4222-8222-222222222222',
    'Elvin Santexnik Xidməti',
    'Mənzillərdə santexnika təmiri və kran quraşdırılması üzrə 8 illik təcrübə.',
    8, 'Pending', 72.50, TRUE, TRUE
)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO master_education (education_id, master_id, institution_name, qualification, field_of_study, year_completed)
VALUES (
    'c1111111-1111-4111-8111-111111111111',
    '22222222-2222-4222-8222-222222222222',
    'Bakı Peşə Təhsil Mərkəzi', 'Peşə təhsili', 'Santexnika', 2018
)
ON CONFLICT (education_id) DO NOTHING;

INSERT INTO master_certificates (certificate_id, master_id, certificate_name, issuer, issued_on, verification_status)
VALUES (
    'c2222222-2222-4222-8222-222222222222',
    '22222222-2222-4222-8222-222222222222',
    'Santexnika üzrə peşə sertifikatı', 'Nümunə Təlim Mərkəzi', '2020-06-01', 'Pending'
)
ON CONFLICT (certificate_id) DO NOTHING;

INSERT INTO master_service_areas (master_id, city, district, radius_km, travel_fee)
VALUES
('22222222-2222-4222-8222-222222222222', 'Bakı', 'Nərimanov', 15, 5.00),
('22222222-2222-4222-8222-222222222222', 'Bakı', 'Nəsimi', 15, 5.00)
ON CONFLICT (master_id, city, district) DO NOTHING;

INSERT INTO master_portfolio (portfolio_item_id, master_id, title, description, media_url, media_type, completed_year)
VALUES (
    'c3333333-3333-4333-8333-333333333333',
    '22222222-2222-4222-8222-222222222222',
    'Mətbəx kranının dəyişdirilməsi',
    'Köhnə kranın sökülməsi və yeni kranın quraşdırılması.',
    'https://example.com/portfolio/faucet-replacement.jpg', 'Image', 2026
)
ON CONFLICT (portfolio_item_id) DO NOTHING;

INSERT INTO master_skills (master_id, skill_id, skill_level, years_practiced)
SELECT '22222222-2222-4222-8222-222222222222', s.skill_id, 'Advanced', 5
FROM skills s
WHERE s.skill_name IN ('Faucet Repair', 'Faucet Replacement', 'Pipe Repair')
ON CONFLICT (master_id, skill_id) DO NOTHING;

INSERT INTO listings (
    listing_id, customer_id, category_id, problem_type_id, title, description, problem_details,
    urgency, city, district, public_location_description, full_address,
    latitude, longitude, address_visibility, budget_min, budget_max, budget_type,
    preferred_at_from, preferred_at_to, status, published_at, expires_at
)
VALUES (
    '33333333-3333-4333-8333-333333333333',
    '11111111-1111-4111-8111-111111111111',
    (SELECT category_id FROM service_categories WHERE slug = 'plumbing'),
    (SELECT problem_type_id FROM problem_types WHERE code = 'faucet_leak'),
    'Mətbəx kranı su axıdır',
    'Kranın alt hissəsindən davamlı su sızır. Təmir və ya dəyişdirilmə lazımdır.',
    '{"leak_location":"base","water_can_be_shut_off":true,"replacement_needed":"unknown"}'::jsonb,
    'Urgent', 'Bakı', 'Nərimanov', 'Nərimanov rayonu, metroya yaxın',
    'Nümunə küçəsi 10, mənzil 15', 40.4093, 49.8671,
    'After_Acceptance', 20.00, 80.00, 'Range',
    ((CURRENT_DATE + 2)::timestamp + TIME '09:00') AT TIME ZONE 'Asia/Baku', ((CURRENT_DATE + 2)::timestamp + TIME '18:00') AT TIME ZONE 'Asia/Baku',
    'Published', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '3 days'
)
ON CONFLICT (listing_id) DO NOTHING;

INSERT INTO listing_attachments (
    attachment_id, listing_id, uploaded_by, file_url, original_file_name, mime_type, file_size_bytes
)
VALUES (
    '44444444-4444-4444-8444-444444444444',
    '33333333-3333-4333-8333-333333333333',
    '11111111-1111-4111-8111-111111111111',
    'https://example.com/listings/faucet-leak.jpg', 'faucet-leak.jpg', 'image/jpeg', 245000
)
ON CONFLICT (attachment_id) DO NOTHING;

INSERT INTO master_offers (
    offer_id, listing_id, master_id, message, proposed_total, currency, price_type,
    labor_cost, materials_cost, travel_cost, other_cost, materials_included,
    possible_extra_cost, estimated_duration_value, estimated_duration_unit,
    available_from, available_to, warranty_days, status, valid_until
)
VALUES (
    '55555555-5555-4555-8555-555555555555',
    '33333333-3333-4333-8333-333333333333',
    '22222222-2222-4222-8222-222222222222',
    'Kranı təxminən 2 saata təmir edə bilərəm. Təmir mümkün olmasa, dəyişdirilməsini razılaşdırarıq.',
    65.00, 'AZN', 'Estimated', 40.00, 20.00, 5.00, 0.00, TRUE,
    FALSE, 2.00, 'Hours',
    ((CURRENT_DATE + 2)::timestamp + TIME '10:00') AT TIME ZONE 'Asia/Baku', ((CURRENT_DATE + 2)::timestamp + TIME '14:00') AT TIME ZONE 'Asia/Baku', 30,
    'Pending', CURRENT_TIMESTAMP + INTERVAL '1 day'
)
ON CONFLICT (listing_id, master_id) DO NOTHING;

-- Optional example of accepting an offer. Execute only when the customer really accepts it.
-- UPDATE master_offers SET status = 'Accepted'
-- WHERE offer_id = '55555555-5555-4555-8555-555555555555';
-- UPDATE listings SET status = 'In_Progress'
-- WHERE listing_id = '33333333-3333-4333-8333-333333333333';
-- INSERT INTO jobs (listing_id, offer_id, customer_id, master_id, agreed_price, status)
-- VALUES (
--   '33333333-3333-4333-8333-333333333333',
--   '55555555-5555-4555-8555-555555555555',
--   '11111111-1111-4111-8111-111111111111',
--   '22222222-2222-4222-8222-222222222222',
--   65.00, 'Agreed'
-- );

COMMIT;

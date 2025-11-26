CREATE TABLE public.device_workflows (
  id integer NOT NULL,
  workflow_id character varying(50) NOT NULL,
  ack boolean,
  division_id character varying(50),
  device_id character varying(50)
);
CREATE SEQUENCE public.device_workflows_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER SEQUENCE public.device_workflows_id_seq OWNED BY public.device_workflows.id;
CREATE TABLE public.devices (
  device_id character varying(255) NOT NULL,
  device_name character varying(255) NOT NULL,
  os_type character varying(255)
);
CREATE SEQUENCE public.devices_device_id_seq
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER SEQUENCE public.devices_device_id_seq OWNED BY public.devices.device_id;
CREATE TABLE public.division_devices (
  id integer NOT NULL,
  division_id character varying(50) NOT NULL,
  device_id character varying(255) NOT NULL
);
CREATE SEQUENCE public.division_devices_id_seq
  AS integer
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;
ALTER SEQUENCE public.division_devices_id_seq OWNED BY public.division_devices.id;
CREATE TABLE public.divisions (
  division_id character varying(50) NOT NULL,
  division_name character varying(30) NOT NULL
);
CREATE TABLE public.workflow (
  unique_id character varying(50) DEFAULT gen_random_uuid() NOT NULL,
  name character varying(255) NOT NULL,
  workflow_type character varying(10) NOT NULL,
  "time" timestamp with time zone DEFAULT now() NOT NULL,
  status character varying(5) NOT NULL,
  notification_type character varying(50) NOT NULL,
  ack boolean DEFAULT false NOT NULL,
  published boolean DEFAULT false NOT NULL,
  body character varying(255),
  priority character varying(3),
  CONSTRAINT workflow_notification_type_check CHECK (((notification_type)::text = ANY ((ARRAY['Single'::character varying, 'Division'::character varying, 'Multi Select'::character varying, 'All'::character varying])::text[]))),
  CONSTRAINT workflow_status_check CHECK (((status)::text = ANY ((ARRAY['live'::character varying, 'draft'::character varying])::text[]))),
  CONSTRAINT workflow_workflow_type_check CHECK (((workflow_type)::text = ANY ((ARRAY['immediate'::character varying, 'scheduled'::character varying])::text[])))
);
ALTER TABLE ONLY public.device_workflows ALTER COLUMN id SET DEFAULT nextval('public.device_workflows_id_seq'::regclass);
ALTER TABLE ONLY public.devices ALTER COLUMN device_id SET DEFAULT nextval('public.devices_device_id_seq'::regclass);
ALTER TABLE ONLY public.division_devices ALTER COLUMN id SET DEFAULT nextval('public.division_devices_id_seq'::regclass);
SELECT pg_catalog.setval('public.device_workflows_id_seq', 782, true);
SELECT pg_catalog.setval('public.devices_device_id_seq', 12, true);
SELECT pg_catalog.setval('public.division_devices_id_seq', 12, true);
ALTER TABLE ONLY public.device_workflows
  ADD CONSTRAINT device_workflows_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.devices
  ADD CONSTRAINT devices_pkey PRIMARY KEY (device_id);
ALTER TABLE ONLY public.division_devices
  ADD CONSTRAINT division_devices_pkey PRIMARY KEY (id);
ALTER TABLE ONLY public.divisions
  ADD CONSTRAINT divisions_pkey PRIMARY KEY (division_id);
ALTER TABLE ONLY public.workflow
  ADD CONSTRAINT workflow_pkey PRIMARY KEY (unique_id);
ALTER TABLE ONLY public.device_workflows
  ADD CONSTRAINT device_workflows_notification_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.workflow(unique_id);
ALTER TABLE ONLY public.division_devices
  ADD CONSTRAINT division_devices_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id);
ALTER TABLE ONLY public.division_devices
  ADD CONSTRAINT division_devices_division_id_fkey FOREIGN KEY (division_id) REFERENCES public.divisions(division_id) ON DELETE CASCADE;
ALTER TABLE ONLY public.device_workflows
  ADD CONSTRAINT fk_device_id_devices FOREIGN KEY (device_id) REFERENCES public.devices(device_id);
ALTER TABLE ONLY public.device_workflows
  ADD CONSTRAINT fk_division_id_divisions FOREIGN KEY (division_id) REFERENCES public.divisions(division_id); 



----------------------------------------------------------------------------------------------------------------------------------------------------------------->

ALTER TABLE public.device_workflows
  ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  ADD COLUMN acknowledged_at TIMESTAMP WITH TIME ZONE;

select * from device_workflows;

select * from devices;

select * from divisions;

select * from division_devices;

select * from workflow;

CREATE TABLE public.screenshots (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    storage_url TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select * from screenshots;

-- Create the FAQ table
CREATE TABLE public.faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    answer TEXT,
    search_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() 
);

-- Add a sequence for FAQ IDs
CREATE SEQUENCE public.faqs_id_seq
  START WITH 1
  INCREMENT BY 1
  NO MINVALUE
  NO MAXVALUE
  CACHE 1;

ALTER SEQUENCE public.faqs_id_seq OWNED BY public.faqs.id;

-- Add the constraint to the table to make the `id` auto-incremented
ALTER TABLE ONLY public.faqs ALTER COLUMN id SET DEFAULT nextval('public.faqs_id_seq'::regclass);

-- Optional: You can create a foreign key if the FAQ is associated with a device or workflow
-- Example: Add device_id to associate FAQ with a device
-- ALTER TABLE public.faqs ADD COLUMN device_id VARCHAR(255);

-- Optional: Create a foreign key relation between FAQ and devices (if necessary)
-- ALTER TABLE public.faqs
--     ADD CONSTRAINT fk_device_id_devices FOREIGN KEY (device_id) REFERENCES public.devices(device_id);

-- Inserting multiple FAQs
INSERT INTO faqs (id, question, answer, search_count, match_count)
VALUES 
  ('1', 'What is a security notification?', 'A security notification is an alert that informs you about a potential or detected security threat related to your account, device, or network.', 0, 0),
  ('2', 'How will I receive a security notification?', 'Security notifications can be delivered through various channels, including: Email, SMS, Push notifications, In-app alerts.', 0, 0),
  ('3', 'What should I do if I receive a security notification?', 'It depends on the type of notification: Suspicious login attempt, Malware alert, Account breach warning.', 0, 0),
  ('4', 'What is two-factor authentication (2FA)?', '2FA adds an extra layer of security to your account by requiring two forms of identification.', 0, 0),
  ('5', 'What should I do if I don’t recognize the activity in the notification?', 'Change your password immediately and enable two-factor authentication (2FA).', 0, 0),
  ('6', 'Can I ignore security notifications?', 'No. Ignoring security notifications can leave your account or device vulnerable to cyber threats.', 0, 0),
  ('8', 'Why am I receiving so many security notifications?', 'Frequent notifications could be due to unusual login attempts or system alerts warning of potential risks.', 0, 0),
  ('9', 'Can I turn off security notifications?', 'In most cases, security notifications cannot be turned off entirely.', 0, 0),
  ('10', 'What if I think my account or device is compromised?', 'Immediately change passwords for your accounts and enable two-factor authentication (if not already activated).', 0, 0);
CREATE TABLE public.auto_screenshot (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL REFERENCES public.devices(device_id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    storage_url TEXT NULL
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE public.auto_screenshot 
ADD COLUMN interval_minutes INT NOT NULL DEFAULT 5 CHECK (interval_minutes > 0);

ALTER TABLE public.auto_screenshot 
ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT TRUE;

https://chatgpt.com/share/67d045f8-b7f8-8004-8607-ce727b089514
--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Homebrew)
-- Dumped by pg_dump version 14.17 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO random_coffee;

--
-- Name: meetings; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.meetings (
    id integer NOT NULL,
    user1_id integer,
    user2_id integer,
    scheduled_at timestamp without time zone,
    status character varying(20),
    created_at timestamp without time zone
);


ALTER TABLE public.meetings OWNER TO random_coffee;

--
-- Name: meetings_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.meetings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.meetings_id_seq OWNER TO random_coffee;

--
-- Name: meetings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.meetings_id_seq OWNED BY public.meetings.id;


--
-- Name: poll_responses; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.poll_responses (
    id integer NOT NULL,
    poll_id integer,
    user_id integer,
    response boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.poll_responses OWNER TO random_coffee;

--
-- Name: poll_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.poll_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.poll_responses_id_seq OWNER TO random_coffee;

--
-- Name: poll_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.poll_responses_id_seq OWNED BY public.poll_responses.id;


--
-- Name: ratings; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.ratings (
    id integer NOT NULL,
    from_user_id integer,
    to_user_id integer,
    meeting_id integer,
    rating integer,
    comment text,
    created_at timestamp without time zone
);


ALTER TABLE public.ratings OWNER TO random_coffee;

--
-- Name: ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ratings_id_seq OWNER TO random_coffee;

--
-- Name: ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.ratings_id_seq OWNED BY public.ratings.id;


--
-- Name: user_preferences; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.user_preferences (
    id integer NOT NULL,
    user_id integer,
    preferred_gender character varying(10),
    age_range_min integer,
    age_range_max integer,
    preferred_languages character varying(100),
    preferred_interests text,
    preferred_meeting_times character varying(50)
);


ALTER TABLE public.user_preferences OWNER TO random_coffee;

--
-- Name: user_preferences_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.user_preferences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_preferences_id_seq OWNER TO random_coffee;

--
-- Name: user_preferences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.user_preferences_id_seq OWNED BY public.user_preferences.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id integer,
    nickname character varying(100),
    age integer,
    gender character varying(10),
    profession character varying(100),
    interests text,
    language character varying(50),
    meeting_time character varying(50),
    created_at timestamp without time zone,
    experience integer,
    total_meetings integer,
    completed_meetings integer,
    average_rating double precision,
    is_active boolean
);


ALTER TABLE public.users OWNER TO random_coffee;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO random_coffee;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: weekly_polls; Type: TABLE; Schema: public; Owner: random_coffee
--

CREATE TABLE public.weekly_polls (
    id integer NOT NULL,
    week_start timestamp without time zone,
    week_end timestamp without time zone,
    poll_message_id integer,
    status character varying(20),
    created_at timestamp without time zone
);


ALTER TABLE public.weekly_polls OWNER TO random_coffee;

--
-- Name: weekly_polls_id_seq; Type: SEQUENCE; Schema: public; Owner: random_coffee
--

CREATE SEQUENCE public.weekly_polls_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.weekly_polls_id_seq OWNER TO random_coffee;

--
-- Name: weekly_polls_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: random_coffee
--

ALTER SEQUENCE public.weekly_polls_id_seq OWNED BY public.weekly_polls.id;


--
-- Name: meetings id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.meetings ALTER COLUMN id SET DEFAULT nextval('public.meetings_id_seq'::regclass);


--
-- Name: poll_responses id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.poll_responses ALTER COLUMN id SET DEFAULT nextval('public.poll_responses_id_seq'::regclass);


--
-- Name: ratings id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.ratings ALTER COLUMN id SET DEFAULT nextval('public.ratings_id_seq'::regclass);


--
-- Name: user_preferences id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.user_preferences ALTER COLUMN id SET DEFAULT nextval('public.user_preferences_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: weekly_polls id; Type: DEFAULT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.weekly_polls ALTER COLUMN id SET DEFAULT nextval('public.weekly_polls_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.alembic_version (version_num) FROM stdin;
570c503e450b
\.


--
-- Data for Name: meetings; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.meetings (id, user1_id, user2_id, scheduled_at, status, created_at) FROM stdin;
\.


--
-- Data for Name: poll_responses; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.poll_responses (id, poll_id, user_id, response, created_at) FROM stdin;
\.


--
-- Data for Name: ratings; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.ratings (id, from_user_id, to_user_id, meeting_id, rating, comment, created_at) FROM stdin;
\.


--
-- Data for Name: user_preferences; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.user_preferences (id, user_id, preferred_gender, age_range_min, age_range_max, preferred_languages, preferred_interests, preferred_meeting_times) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.users (id, telegram_id, nickname, age, gender, profession, interests, language, meeting_time, created_at, experience, total_meetings, completed_meetings, average_rating, is_active) FROM stdin;
\.


--
-- Data for Name: weekly_polls; Type: TABLE DATA; Schema: public; Owner: random_coffee
--

COPY public.weekly_polls (id, week_start, week_end, poll_message_id, status, created_at) FROM stdin;
\.


--
-- Name: meetings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.meetings_id_seq', 1, false);


--
-- Name: poll_responses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.poll_responses_id_seq', 1, false);


--
-- Name: ratings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.ratings_id_seq', 1, false);


--
-- Name: user_preferences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.user_preferences_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- Name: weekly_polls_id_seq; Type: SEQUENCE SET; Schema: public; Owner: random_coffee
--

SELECT pg_catalog.setval('public.weekly_polls_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: meetings meetings_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.meetings
    ADD CONSTRAINT meetings_pkey PRIMARY KEY (id);


--
-- Name: poll_responses poll_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_pkey PRIMARY KEY (id);


--
-- Name: ratings ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_pkey PRIMARY KEY (id);


--
-- Name: user_preferences user_preferences_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_pkey PRIMARY KEY (id);


--
-- Name: user_preferences user_preferences_user_id_key; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_user_id_key UNIQUE (user_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_telegram_id_key UNIQUE (telegram_id);


--
-- Name: weekly_polls weekly_polls_pkey; Type: CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.weekly_polls
    ADD CONSTRAINT weekly_polls_pkey PRIMARY KEY (id);


--
-- Name: meetings meetings_user1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.meetings
    ADD CONSTRAINT meetings_user1_id_fkey FOREIGN KEY (user1_id) REFERENCES public.users(id);


--
-- Name: meetings meetings_user2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.meetings
    ADD CONSTRAINT meetings_user2_id_fkey FOREIGN KEY (user2_id) REFERENCES public.users(id);


--
-- Name: poll_responses poll_responses_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.weekly_polls(id);


--
-- Name: poll_responses poll_responses_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.poll_responses
    ADD CONSTRAINT poll_responses_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: ratings ratings_from_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_from_user_id_fkey FOREIGN KEY (from_user_id) REFERENCES public.users(id);


--
-- Name: ratings ratings_meeting_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES public.meetings(id);


--
-- Name: ratings ratings_to_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.ratings
    ADD CONSTRAINT ratings_to_user_id_fkey FOREIGN KEY (to_user_id) REFERENCES public.users(id);


--
-- Name: user_preferences user_preferences_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: random_coffee
--

ALTER TABLE ONLY public.user_preferences
    ADD CONSTRAINT user_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--


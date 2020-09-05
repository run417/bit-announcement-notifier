--
-- PostgreSQL database dump
--

-- Dumped from database version 12.4
-- Dumped by pg_dump version 12.4

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
-- Name: announcement; Type: TABLE; Schema: public; Owner: ban_app_user_01
--

CREATE TABLE public.announcement (
    id integer NOT NULL,
    title character varying(255) NOT NULL,
    url character varying(255) NOT NULL,
    check_string character varying(255) NOT NULL,
    published_datetime timestamp without time zone NOT NULL,
    retrieved_datetime timestamp without time zone NOT NULL,
    stored_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_datetime timestamp without time zone NOT NULL
);


ALTER TABLE public.announcement OWNER TO ban_app_user_01;

--
-- Name: announcement_id_seq; Type: SEQUENCE; Schema: public; Owner: ban_app_user_01
--

CREATE SEQUENCE public.announcement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.announcement_id_seq OWNER TO ban_app_user_01;

--
-- Name: announcement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ban_app_user_01
--

ALTER SEQUENCE public.announcement_id_seq OWNED BY public.announcement.id;


--
-- Name: announcement id; Type: DEFAULT; Schema: public; Owner: ban_app_user_01
--

ALTER TABLE ONLY public.announcement ALTER COLUMN id SET DEFAULT nextval('public.announcement_id_seq'::regclass);


--
-- Name: announcement announcement_check_string_key; Type: CONSTRAINT; Schema: public; Owner: ban_app_user_01
--

ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_check_string_key UNIQUE (check_string);


--
-- Name: announcement announcement_pkey; Type: CONSTRAINT; Schema: public; Owner: ban_app_user_01
--

ALTER TABLE ONLY public.announcement
    ADD CONSTRAINT announcement_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--


-- dbo.users definition

-- Drop table

-- DROP TABLE dbo.users;

CREATE TABLE tharun.usersbm (
	user_id int4 NULL,
	"name" varchar(40) NULL,
	email varchar(40) NULL,
	city varchar(100) NULL,
	CONSTRAINT users_user_id_key UNIQUE (user_id)
);

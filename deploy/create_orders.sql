CREATE TABLE orders (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id), item TEXT NOT NULL);

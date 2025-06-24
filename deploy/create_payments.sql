CREATE TABLE payments (id SERIAL PRIMARY KEY, order_id INT REFERENCES orders(id), amount NUMERIC NOT NULL);

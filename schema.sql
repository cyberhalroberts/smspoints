create table users (
    users_id integer primary key,
    name text not null,
    color text null,
    email text unique not null,
    admin boolean default false not null
);

create index if not exists users_email on users(email);

create table points (
    points_id int primary key,
    users_id int not null,
    created_time text default current_timestamp not null,
    event_date text not null,
    event_type text not null,
    event_description text null,

    foreign key (users_id) references users(id)
);

create index if not exists points_user on points(users_id);
create index if not exists points_created on points(created_time);
create index if not exists points_event_day on points(event_day);
create index if not exists points_event_type on points(event_type);

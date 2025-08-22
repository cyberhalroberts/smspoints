create table users (
    users_id integer primary key,
    name text not null,
    color text check (color in ('blue', 'white')) null,
    email text unique not null,
    admin boolean default false not null,
    teacher_points int default 0
);

create index if not exists users_email on users(email);

create table points (
    points_id int primary key,
    num_points int not null default 1,
    users_id int null,
    created_time text default current_timestamp not null,
    event_date text not null,
    event_type text not null,
    event_description text null,
    added_by int not null,
    color text check (color in ('blue', 'white')) null,

    foreign key (users_id) references users(id),
    foreign key (added_by) references users(id)
);

create index if not exists points_user on points(users_id);
create index if not exists points_created on points(created_time);
create index if not exists points_event_day on points(event_date);
create index if not exists points_event_type on points(event_type);

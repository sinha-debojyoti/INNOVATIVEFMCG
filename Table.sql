create table `database`.product_details
(
    BARCODE        int          not null,
    `Product Name` varchar(256) null,
    category       varchar(256) null,
    weight         int          null,
    MRP            float        null,
    descrip        varchar(256) null,
    cream          varchar(256) null,
    constraint product_details_barcode_uindex
        unique (BARCODE)
);

alter table `database`.product_details
    add primary key (BARCODE);

create table `database`.product_review
(
    barcode        int null,
    product_rating int null,
    constraint table_name_product_details_BARCODE_fk
        foreign key (barcode) references `database`.product_details (BARCODE)
);

create table `database`.shop_details
(
    shop_id   int          not null,
    shop_name varchar(256) null,
    address   varchar(256) null,
    pasword   varchar(256) null,
    latitude  double       null,
    longitude double       null,
    contact   varchar(10)  null,
    primary key (shop_id)
);

create table `database`.product_stocks
(
    `S.N.`        int   null,
    shop_id       int   null,
    quantity      int   null,
    selling_price float null,
    constraint product_stocks_product_details_BARCODE_fk
        foreign key (`S.N.`) references `database`.product_details (BARCODE),
    constraint product_stocks_shop_details_shop_id_fk
        foreign key (shop_id) references `database`.shop_details (shop_id)
);

create table `database`.shop_review
(
    shop_id     int null,
    shop_rating int null,
    constraint shop_review_shop_details_shop_id_fk
        foreign key (shop_id) references `database`.shop_details (shop_id)
);


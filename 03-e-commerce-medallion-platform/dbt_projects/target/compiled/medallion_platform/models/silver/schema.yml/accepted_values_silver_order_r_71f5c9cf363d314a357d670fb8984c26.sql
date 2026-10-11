
    
    

with all_values as (

    select
        review_score as value_field,
        count(*) as n_records

    from `dbt-medallion`.`silver`.`silver_order_reviews`
    group by review_score

)

select *
from all_values
where value_field not in (
    '1','2','3','4','5'
)



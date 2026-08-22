from models import db, Customer


def get_or_create_customer(
    business_id,
    customer_phone,
    customer_name=""
):

    customer = Customer.query.filter_by(
        business_id=business_id,
        phone=customer_phone
    ).first()

    if customer:

        if customer_name:
            customer.name = customer_name
            db.session.commit()

        return customer

    customer = Customer(
        business_id=business_id,
        phone=customer_phone,
        name=customer_name or ""
    )

    db.session.add(customer)
    db.session.commit()

    return customer
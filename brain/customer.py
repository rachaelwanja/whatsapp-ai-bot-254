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
            customer.name = customer_name.strip()
            db.session.commit()

        return customer

    customer = Customer(
        business_id=business_id,
        phone=customer_phone,
        name=customer_name.strip()
        if customer_name
        else ""
    )

    db.session.add(customer)
    db.session.commit()

    return customer


def update_customer_name(
    customer,
    customer_name
):

    if not customer_name:
        return customer

    customer.name = customer_name.strip()

    db.session.commit()

    return customer
    
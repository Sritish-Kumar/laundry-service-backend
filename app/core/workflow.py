from app.core.constants import OrderStatus, UserRole


VALID_ORDER_TRANSITIONS = {

    OrderStatus.PENDING_PICKUP: [
        OrderStatus.PICKED_UP,
        OrderStatus.CANCELLED
    ],

    OrderStatus.PICKED_UP: [
        OrderStatus.RECEIVED,
        OrderStatus.CANCELLED
    ],

    OrderStatus.RECEIVED: [
        OrderStatus.SORTING,
        # Staff/Admin bulk shortcut for pre-processed orders that skip the
        # internal sorting/washing/drying/packing pipeline.
        OrderStatus.OUT_FOR_DELIVERY
    ],

    OrderStatus.SORTING: [
        OrderStatus.WASHING
    ],

    OrderStatus.WASHING: [
        OrderStatus.DRYING
    ],

    OrderStatus.DRYING: [
        OrderStatus.IRONING,
        OrderStatus.PACKING
    ],

    OrderStatus.IRONING: [
        OrderStatus.PACKING
    ],

    OrderStatus.PACKING: [
        OrderStatus.OUT_FOR_DELIVERY
    ],

    OrderStatus.OUT_FOR_DELIVERY: [
        OrderStatus.DELIVERED
    ],

    OrderStatus.DELIVERED: [],

    OrderStatus.CANCELLED: []
}


# Answers "who is allowed to perform this transition", independently of
# whether the transition itself is valid (VALID_ORDER_TRANSITIONS answers
# that question). Both checks must pass.
TRANSITION_PERMISSIONS: dict[tuple[OrderStatus, OrderStatus], list[UserRole]] = {

    (OrderStatus.PENDING_PICKUP, OrderStatus.PICKED_UP): [
        UserRole.DELIVERY_AGENT, UserRole.ADMIN
    ],
    (OrderStatus.PENDING_PICKUP, OrderStatus.CANCELLED): [
        UserRole.CUSTOMER, UserRole.STAFF, UserRole.ADMIN
    ],

    (OrderStatus.PICKED_UP, OrderStatus.RECEIVED): [UserRole.STAFF, UserRole.ADMIN],
    (OrderStatus.PICKED_UP, OrderStatus.CANCELLED): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.RECEIVED, OrderStatus.SORTING): [UserRole.STAFF, UserRole.ADMIN],
    (OrderStatus.RECEIVED, OrderStatus.OUT_FOR_DELIVERY): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.SORTING, OrderStatus.WASHING): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.WASHING, OrderStatus.DRYING): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.DRYING, OrderStatus.IRONING): [UserRole.STAFF, UserRole.ADMIN],
    (OrderStatus.DRYING, OrderStatus.PACKING): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.IRONING, OrderStatus.PACKING): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.PACKING, OrderStatus.OUT_FOR_DELIVERY): [UserRole.STAFF, UserRole.ADMIN],

    (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED): [
        UserRole.DELIVERY_AGENT, UserRole.ADMIN
    ],
}


# For DELIVERY_AGENT transitions that also require the agent to be the one
# actually assigned to the order (ADMIN is exempt — operational override).
# Maps a (from, to) pair to the Order column name holding the assigned agent.
AGENT_OWNERSHIP_TRANSITIONS: dict[tuple[OrderStatus, OrderStatus], str] = {
    (OrderStatus.PENDING_PICKUP, OrderStatus.PICKED_UP): "pickup_agent_id",
    (OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED): "delivery_agent_id",
}
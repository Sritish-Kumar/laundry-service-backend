from app.core.constants import OrderStatus


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
        OrderStatus.SORTING
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
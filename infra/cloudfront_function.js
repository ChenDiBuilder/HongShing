function handler(event) {
    // Keep the /product-demo/hongshing prefix so the ALB can route by path
    return event.request;
}

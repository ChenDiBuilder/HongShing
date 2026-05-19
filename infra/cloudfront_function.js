function handler(event) {
    var request = event.request;
    var prefix = "/product-demo/hongshing";
    if (request.uri.startsWith(prefix + "/api/")) {
        request.uri = request.uri.substring(prefix.length);
    }
    return request;
}

module.exports = {
    runtimeCompiler: true,
    configureWebpack: {
        devtool: 'source-map'
    },
    devServer: {
        disableHostCheck: true,
        proxy: {
            "^/ws": {
                target: "http://localhost:8000",
                ws: true,
                secure: false
            },
            "^/admin": {
                target: "http://localhost:8000",
                secure: false
            },
            "^/dev": {
                target: "http://localhost:8000",
                secure: false
            },
            "^/static/admin": {
                target: "http://localhost:8000",
                secure: false
            },
        }
    }
}
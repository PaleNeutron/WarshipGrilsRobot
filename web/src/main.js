import Vue from 'vue'
import App from './App.vue'
import store from './store'
import VueNativeSock from 'vue-native-websocket-es5'
import colors from 'vuetify/es5/util/colors'
import router from "./router"
import  "babel-polyfill"


import Vuetify from 'vuetify'
Vue.use(Vuetify, {
    theme: {
        primary: "#E98300",
        secondary: "#0066A1",
        accent: "#899F99",
        error: "#CD202C",
        warning: "#FCD450",
        info: "#3DB7E4",
        success: "#D6E342"
    }
})

Vue.config.productionTip = false

var loc = window.location;
var new_uri;
if (loc.protocol === "https:") {
    new_uri = "wss:";
} else {
    new_uri = "ws:";
}
new_uri += "//" + loc.host;
Vue.use(VueNativeSock, new_uri + '/ws/dev/log/', {
    format: 'json',
    reconnection: true, // (Boolean) whether to reconnect automatically (false)
    reconnectionAttempts: 5, // (Number) number of reconnection attempts before giving up (Infinity),
    reconnectionDelay: 3000, // (Number) how long to initially wait before attempting a new (1000)
})

new Vue({
    store,
    router,
    iconfont: 'fa',
    render: h => h(App),
    created: function () {
        // `this` points to the vm instance
        this.$options.sockets.onopen = () => {
            this.$socket.send("init")
        }
    }
}).$mount('#app')



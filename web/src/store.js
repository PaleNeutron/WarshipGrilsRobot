import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
    state: {
        nav_show: false
    },
    mutations: {
        set_nav_show(state, value){
            state.nav_show = value
        }
    },
    actions: {}
})

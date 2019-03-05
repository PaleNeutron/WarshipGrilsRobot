import VueRouter from 'vue-router'
import Vue from "vue";
import logpage from "./components/logpage"
import einfo from "./components/ElevatorInfo"
import rinfo from "./components/RobotInfo"

Vue.use(VueRouter);
export default new VueRouter({
    routes: [
        {
            path:"/log", component:logpage
        },
        {
            path:"/", component: einfo
        },
        {
            path:"/robot", component: rinfo
        }
    ]
})

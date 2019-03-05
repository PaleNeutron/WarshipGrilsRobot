<template>
    <div id="app">
        <v-app top-toolbar left-sidebar>
            <toolbar v-on:iconClicked="showSidebar" @append="append_list"></toolbar>
            <sidebar :drawer="drawer"></sidebar>
            <app-main :isSmallScreen="isSmallScreen"></app-main>
        </v-app>
    </div>
</template>

<script>
    import Sidebar from './components/layout/Sidebar.vue'
    import Toolbar from './components/layout/Toolbar.vue'
    import AppMain from './components/layout/AppMain.vue'

    export default {
        name: 'app',

        components: {
            Sidebar,
            Toolbar,
            AppMain
        },

        methods: {
            handleResize () {
                let width = (window.innerWidth > 0) ? window.innerWidth : screen.width
                if (width < 1024) {
                    this.isSmallScreen = true
                    this.drawer = false
                    this.removeOverlay()
                } else {
                    this.isSmallScreen = false
                    this.drawer = true
                    this.removeOverlay()
                }
            },

            showSidebar () {
                this.drawer = !this.drawer
            },

            append_list(){
                console.log(this.test_list);
                this.test_list.push("c")
            },

            removeOverlay () {
                let $overlay = document.getElementsByClassName('overlay')
                if ($overlay.length > 0) {
                    $overlay[0].classList.remove('overlay--active')
                }
            }
        },

        data() {
            return {
                drawer: false,
                isIconClicked: false,
                isSmallScreen: false,
                test_list: ["a" , "b"]
            }
        },

        mounted () {
            this.handleResize()
            window.addEventListener('resize', this.handleResize)
        },

        beforeDestroy () {
            window.removeEventListener('resize', this.handleResize)
        }
    }
</script>

<style lang="stylus">
    @import '../node_modules/font-awesome/css/font-awesome.min.css'
    @import '../node_modules/vuetify/src/stylus/main';
    @import 'css/google-material-icons.css';
    @import 'css/main.css';
</style>

<template>
    <v-navigation-drawer  v-model="should_show"
                          class="elevation-5 sidebar"
                          fixed
                          temporary>
        <v-container class="avatar-container text-xs-center pt-5">
            <div class="image-cropper elevation-1 mb-4">
                <img class="avatar" src="../../assets/te.png">
            </div>
            <p class="avatar-header">
                Elevtor Robot
            </p>
            <hr>
            <v-btn  class="my-3"
                    id="connect_robots"
                    @click="connect_robots">Connect Robots</v-btn>
            <v-btn  class="my-3"
                    id="admin"
                    href="admin/"
                    target="_blank"
            >Settings</v-btn>
        </v-container>

        <v-list dense>
            <!--<v-list-item v-for="item in menuitems" :key="item">-->
            <!--<v-list-tile :href="item.path" :router="item.router">-->
            <!--<v-list-tile-avatar>-->
            <!--<v-icon>{{ item.icon }}</v-icon>-->
            <!--</v-list-tile-avatar>-->
            <!--<v-list-tile-content>-->
            <!--<v-list-tile-title class="list-title">{{ item.title }}</v-list-tile-title>-->
            <!--</v-list-tile-content>-->
            <!--</v-list-tile>-->
            <!--</v-list-item>-->
        </v-list>

        <v-container fluid>
            <v-layout row justify-space-around class="contact-layout">
                <!--<v-btn v-for="(contact, index) in contacts" :key="index"-->
                <!--floating small :class="[contact.color]"-->
                <!--v-tooltip:top="{ html: contact.tooltip }"-->
                <!--@click.native="onContactMethodClicked(contact.link)"-->
                <!--&gt;-->
                <!--<v-icon light fa class="contact-icon">{{ contact.icon }}</v-icon>-->
                <!--</v-btn>-->
            </v-layout>
        </v-container>
    </v-navigation-drawer>
</template>

<script>
    import axios from 'axios';
    export default {
        name: 'Sidebar',

        props: ['drawer', 'isSmallScreen', 'isIconClicked'],

        data() {
            return {
                showSidebar: this.drawer
            }
        },

        // watch: {
        //   drawer () {
        //     this.showSidebar = this.drawer
        //     console.log('drawer: ' + this.showSidebar)
        //   },
        //
        //   isIconClicked() {
        //     this.showSidebar = true
        //   }
        // },

        computed: {
            should_show: {
                get() {
                    return this.$store.state.nav_show
                },
                set(value) {
                    this.$store.commit('set_nav_show', value)
                }
            }
        },
        //
        methods: {
            //   ...mapActions([
            //     'readContacts'
            //   ]),
            onContactMethodClicked(link) {
                if (link) {
                    if (link.includes('@')) {
                        link = 'mailto:' + link
                    }
                    window.open(link)
                }
            },
            connect_robots() {
                axios.get("dev/robot/connect")
            }
        },

        created() {
            // this.readContacts()
        }
    }
</script>

<style lang="stylus" scoped>
    /* sidebar */
    /* avatar */
    .avatar-container {
        text-align: center;
    }

    .image-cropper {
        width: 175px;
        height: 100px;
        position: relative;
        overflow: hidden;
        margin: 0 auto;
    }

    .avatar-header {
        margin-top: 10px;
    }

    .avatar {
        display: inline;
        margin: 0 auto;
        height: 100%;
        width: auto;
    }

    /* active tab */
    .list__tile--active .list__tile__title {
        font-weight: bold;
        color: #58acff !important;
    }

    .list__tile__title {
        font-size: 14px;
        color: #424242;
        margin-left: 10px;
    }

    /* Contact buttons */
    .contact-layout {
        margin: 10px 0;
    }

    .contact-icon {
        font-size: 20px;
    }

    .btn--floating.btn--small, .fab--floating.btn--small, .fab.btn--small {
        width: 35px;
        height: 35px;
    }
</style>
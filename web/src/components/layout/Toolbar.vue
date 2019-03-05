<template>
    <div>
        <v-toolbar flat></v-toolbar>
        <v-toolbar fixed color="primary">
            <v-toolbar-side-icon @click.native.stop="onIconClicked"></v-toolbar-side-icon>
            <v-toolbar-title>{{ title }}</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-toolbar-items>
                <v-btn flat to="/">Elevator</v-btn>
                <v-btn flat to="/robot" >Robot</v-btn>
                <v-btn flat to="/log">Logs</v-btn>
            </v-toolbar-items>
        </v-toolbar>
    </div>
</template>

<script>
    export default {
        name: 'Toolbar',
        methods: {
            onIconClicked() {
                this.$store.commit('set_nav_show', !this.$store.state.nav_show)
            },
            onButtonOneClicked(){
                this.$emit('append')
            }
        },
        data (){
            return {
                title: "Elevator Robot"
            }
        }
    }
</script>

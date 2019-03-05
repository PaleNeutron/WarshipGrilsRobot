<template>
    <main id="main">
        <v-container fluid>
            <!--<v-btn>default</v-btn>-->
            <!--<v-btn dark to="/log" >dark</v-btn>-->
            <!--<v-btn color="primary">primary</v-btn>-->
            <!--<v-btn color="secondary">secondary</v-btn>-->
            <keep-alive>
                <router-view></router-view>
            </keep-alive>
        </v-container>
    </main>
</template>

<script>
    export default {
        name: 'AppMain'
    }
</script>

<style scoped>
    main {
        padding-left: 250px;
        padding-right: 250px;
    }

    @media only screen and (max-width: 1024px) {
        main {
            padding-left: 0;
            padding-right: 0;
        }
    }
</style>
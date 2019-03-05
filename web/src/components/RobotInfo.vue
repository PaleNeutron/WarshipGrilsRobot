<template>
    <v-container>
        <v-card v-for="item in name_list"
                :key="item"
                class="my-3" color="info">
            <v-card-title color="secondary">
                <h2>Robot{{ item }}</h2>
            </v-card-title>
            <v-card-text  color="primary">Here is detailed Robot Info</v-card-text>
        </v-card>
    </v-container>
</template>

<script>
    export default {
        name: "RobotInfo",
        data (){
            return{
                name_list : [1,2,3]
            }
        },
        methods:{

        }
    }
</script>

<style scoped>

</style>